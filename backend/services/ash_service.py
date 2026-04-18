"""Player + Ash-level operations. Ash is clamped 0..10 and all changes are logged.

The AI responds TO ash level but never sets it – changes come from hardcoded
in-game choice points (spec §8.2)."""

import json
from datetime import datetime, timezone

from database import get_db

ASH_MIN = 0
ASH_MAX = 10


async def init_player(player_id: str) -> dict:
    """Insert or fetch a player row; update last_seen. Returns
    {"ash_level": int, "is_new": bool}."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT ash_level FROM players WHERE id = ?",
            (player_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO players (id, ash_level, ash_log) VALUES (?, 0, '[]')",
                (player_id,),
            )
            await db.commit()
            return {"ash_level": 0, "is_new": True}

        await db.execute(
            "UPDATE players SET last_seen = CURRENT_TIMESTAMP WHERE id = ?",
            (player_id,),
        )
        await db.commit()
        return {"ash_level": row["ash_level"], "is_new": False}


async def get_player(player_id: str) -> dict | None:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, ash_level, ash_log, created_at, last_seen FROM players WHERE id = ?",
            (player_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_ash(player_id: str, delta: int, reason: str) -> dict:
    """Clamp result between 0 and 10, log to ash_log. Returns
    {"new_ash_level": int, "capped": bool}."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT ash_level, ash_log FROM players WHERE id = ?",
            (player_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            raise ValueError(f"Unknown player: {player_id}")

        current = row["ash_level"]
        target = current + delta
        clamped = max(ASH_MIN, min(ASH_MAX, target))
        capped = clamped != target

        try:
            log = json.loads(row["ash_log"]) if row["ash_log"] else []
        except json.JSONDecodeError:
            log = []

        log.append({
            "delta": delta,
            "reason": reason,
            "ts": datetime.now(timezone.utc).isoformat(),
        })

        await db.execute(
            "UPDATE players SET ash_level = ?, ash_log = ? WHERE id = ?",
            (clamped, json.dumps(log), player_id),
        )
        await db.commit()

        return {"new_ash_level": clamped, "capped": capped}


async def set_ash_level(player_id: str, ash_level: int) -> None:
    """Used by the dialogue endpoint to sync the client-supplied ash_level
    (spec §5.3 step 11)."""
    ash_level = max(ASH_MIN, min(ASH_MAX, ash_level))
    async with get_db() as db:
        await db.execute(
            "UPDATE players SET ash_level = ? WHERE id = ?",
            (ash_level, player_id),
        )
        await db.commit()


async def reset_player(player_id: str) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE players SET ash_level = 0, ash_log = '[]' WHERE id = ?",
            (player_id,),
        )
        await db.commit()
