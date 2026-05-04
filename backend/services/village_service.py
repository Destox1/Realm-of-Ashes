"""Village rumour pool — the cross-NPC awareness layer (project USP).

Every meaningful Ash event is logged here in addition to the player's ash_log.
When ANY NPC is prompted, we read the most-recent N events from this table and
inject them as a "What People in the Village Are Saying" section in the system
prompt. That's how Kael can naturally reference Mira's stolen coins without us
hard-coding any per-NPC scripts.

`summary` is stored in German because that is the language NPCs speak; it goes
verbatim into the prompt. The mapping from event_type → German summary lives
here (server-side) so the frontend only has to send the event_type id.
"""

from database import get_db

# How many recent rumours each NPC sees in their system prompt. Kept small to
# avoid prompt bloat and to focus the NPC on the most-recent moral signal.
DEFAULT_RECENT_LIMIT = 5

# Maps the frontend's ASH_EVENTS[].id to a third-person German rumour sentence
# that reads naturally as village gossip ("Der Fremde stahl von Miras Stand").
# When a new ash event is added in main.js, add its rumour here too.
RUMOR_MAP: dict[str, str] = {
    "steal_mira":      "Der Fremde stahl Münzen von Miras Stand.",
    "help_lena":       "Der Fremde half der kleinen Lena, ihr verlorenes Holzpferd zu finden.",
    "threaten_kael":   "Der Fremde bedrohte Kael den Schmied, um einen niedrigeren Preis zu erpressen.",
    "give_beggar":     "Der Fremde gab dem aschekranken Bettler eine Münze.",
    "thorn_1":         "Der Fremde nahm Thorns dunkles Angebot an.",
    "thorn_2":         "Der Fremde kehrte zu Thorn zurück und nahm noch mehr von dem, was er anbietet.",
    "report_mira":     "Der Fremde meldete Miras Diebstahl bei Ältester Voss.",
    "destroy_garden":  "Der Fremde zertrampelte den Heilkräutergarten des Dorfes.",
    "pray_shrine":     "Der Fremde betete still am Dorfschrein.",
    "corruption_tick": "Der Fremde verweilt zu lange in der Asche-Zone am Rande des Dorfes.",
}


def get_rumor_for(event_type: str) -> str | None:
    """Return the German village-gossip sentence for this event_type, or None
    if we don't have a rumour mapped (in which case the event still updates
    ash but does NOT enter the village rumour pool — by design, so we don't
    pollute the prompt with debug events)."""
    return RUMOR_MAP.get(event_type)


async def record_village_event(player_id: str, event_type: str) -> bool:
    """Log a village-wide rumour. Returns True if a row was written, False if
    the event_type has no mapped rumour (silently ignored)."""
    summary = get_rumor_for(event_type)
    if summary is None:
        return False

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO village_events (player_id, event_type, summary)
            VALUES (?, ?, ?)
            """,
            (player_id, event_type, summary),
        )
        await db.commit()
    return True


async def get_recent_village_events(
    player_id: str, limit: int = DEFAULT_RECENT_LIMIT
) -> list[dict]:
    """Return the N most-recent rumours about this player, NEWEST FIRST.
    Each row: {event_type, summary, fired_at}. Used by claude_service to build
    the "What People in the Village Are Saying" prompt block."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT event_type, summary, fired_at
              FROM village_events
             WHERE player_id = ?
             ORDER BY fired_at DESC, id DESC
             LIMIT ?
            """,
            (player_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def delete_all_for_player(player_id: str) -> None:
    """Reset helper — wipe this player's rumour pool. Called from the reset
    endpoint together with memory_service.delete_all_for_player()."""
    async with get_db() as db:
        await db.execute(
            "DELETE FROM village_events WHERE player_id = ?", (player_id,)
        )
        await db.commit()
