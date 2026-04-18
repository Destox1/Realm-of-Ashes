"""NPC memory + dialogue log CRUD. Enforces spec §4.2 rules:
- Max 10 memories per (player, npc); FIFO delete oldest non-emotional when exceeded.
- Emotional memories are protected (never auto-deleted) and count separately up to 3.
- Dialogue log retained indefinitely but only last 6 exchanges sent to Claude.
"""

from database import get_db

MEMORY_LIMIT_GENERAL = 10
MEMORY_LIMIT_EMOTIONAL = 3
DIALOGUE_HISTORY_DEFAULT = 6


async def get_memories(player_id: str, npc_id: str) -> list[dict]:
    """Return up to MEMORY_LIMIT_GENERAL newest memories for this (player, npc)."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, memory_text, memory_type, created_at
              FROM npc_memories
             WHERE player_id = ? AND npc_id = ?
             ORDER BY created_at DESC
             LIMIT ?
            """,
            (player_id, npc_id, MEMORY_LIMIT_GENERAL + MEMORY_LIMIT_EMOTIONAL),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def insert_memory(
    player_id: str, npc_id: str, memory_text: str, memory_type: str = "general"
) -> None:
    """Insert a memory, then enforce the spec's FIFO / emotional-protection rules."""
    memory_text = memory_text[:120]  # spec hard cap
    if memory_type not in ("general", "emotional", "ash_event"):
        memory_type = "general"

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO npc_memories (player_id, npc_id, memory_text, memory_type)
            VALUES (?, ?, ?, ?)
            """,
            (player_id, npc_id, memory_text, memory_type),
        )
        await db.commit()

    await _enforce_memory_limit(player_id, npc_id)


async def _enforce_memory_limit(player_id: str, npc_id: str) -> None:
    """Delete oldest non-emotional memories when over limit. Emotional memories
    are never auto-deleted but are capped separately at MEMORY_LIMIT_EMOTIONAL."""
    async with get_db() as db:
        # Non-emotional FIFO pruning
        cursor = await db.execute(
            """
            SELECT id FROM npc_memories
             WHERE player_id = ? AND npc_id = ?
               AND memory_type != 'emotional'
             ORDER BY created_at ASC
            """,
            (player_id, npc_id),
        )
        non_emotional_ids = [r["id"] for r in await cursor.fetchall()]
        overflow = len(non_emotional_ids) - MEMORY_LIMIT_GENERAL
        if overflow > 0:
            to_delete = non_emotional_ids[:overflow]
            placeholders = ",".join("?" for _ in to_delete)
            await db.execute(
                f"DELETE FROM npc_memories WHERE id IN ({placeholders})",
                to_delete,
            )

        # Emotional FIFO pruning (protect limit_emotional newest)
        cursor = await db.execute(
            """
            SELECT id FROM npc_memories
             WHERE player_id = ? AND npc_id = ?
               AND memory_type = 'emotional'
             ORDER BY created_at ASC
            """,
            (player_id, npc_id),
        )
        emotional_ids = [r["id"] for r in await cursor.fetchall()]
        e_overflow = len(emotional_ids) - MEMORY_LIMIT_EMOTIONAL
        if e_overflow > 0:
            to_delete = emotional_ids[:e_overflow]
            placeholders = ",".join("?" for _ in to_delete)
            await db.execute(
                f"DELETE FROM npc_memories WHERE id IN ({placeholders})",
                to_delete,
            )

        await db.commit()


async def insert_dialogue_log(
    player_id: str, npc_id: str, role: str, content: str, ash_level: int
) -> None:
    """Append a single turn to dialogue_log."""
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO dialogue_log
                (player_id, npc_id, role, content, ash_level_at_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (player_id, npc_id, role, content, ash_level),
        )
        await db.commit()


async def get_dialogue_history(
    player_id: str, npc_id: str, limit: int = DIALOGUE_HISTORY_DEFAULT
) -> list[dict]:
    """Return the last `limit` exchanges (each exchange = 2 rows: player + npc).
    Ordered oldest -> newest so they map to a chat message array."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT role, content FROM dialogue_log
             WHERE player_id = ? AND npc_id = ?
             ORDER BY id DESC
             LIMIT ?
            """,
            (player_id, npc_id, limit * 2),
        )
        rows = [dict(r) for r in await cursor.fetchall()]
        return list(reversed(rows))


async def delete_all_for_player(player_id: str) -> None:
    """Reset endpoint helper – wipe player's memories and dialogue log."""
    async with get_db() as db:
        await db.execute("DELETE FROM npc_memories WHERE player_id = ?", (player_id,))
        await db.execute("DELETE FROM dialogue_log WHERE player_id = ?", (player_id,))
        await db.commit()
