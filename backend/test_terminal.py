"""Manual Phase-1 milestone test (spec §12 Phase 1).

Usage:
    cd backend
    # make sure .env has ANTHROPIC_API_KEY set
    python test_terminal.py

This script talks to the services directly (no HTTP server needed). It proves:
  1. Kael responds in character at low ash.
  2. Memory extraction stores new facts.
  3. After ash is bumped to 7, Kael's tone visibly shifts.
  4. Memory persists across the ash shift.
"""

import asyncio
import sys
import uuid
from textwrap import fill

from database import init_db
from services import ash_service
from services.claude_service import extract_and_store_memory, generate_dialogue
from services.memory_service import get_memories, insert_dialogue_log

NPC_ID = "kael"
INDENT = "  "


def _box(title: str) -> None:
    bar = "=" * 72
    print(f"\n{bar}\n {title}\n{bar}")


def _wrap(text: str, indent: str = INDENT) -> str:
    return fill(text, width=70, initial_indent=indent, subsequent_indent=indent)


async def _send(player_id: str, message: str, ash_level: int) -> str:
    print(f"\n[PLAYER, ash={ash_level}] {message}")
    response = await generate_dialogue(
        npc_id=NPC_ID,
        player_message=message,
        ash_level=ash_level,
        player_id=player_id,
    )
    print(f"[KAEL]\n{_wrap(response)}")

    await insert_dialogue_log(player_id, NPC_ID, "player", message, ash_level)
    await insert_dialogue_log(player_id, NPC_ID, "npc", response, ash_level)

    # Synchronous memory extraction so we can see the result immediately in the test.
    remembered = await extract_and_store_memory(
        player_id, NPC_ID, message, response
    )
    print(f"[MEMORY EXTRACTED?] {remembered}")

    memories = await get_memories(player_id, NPC_ID)
    if memories:
        print("[KAEL NOW REMEMBERS]")
        for m in memories:
            mark = "⚠" if m["memory_type"] == "emotional" else "•"
            print(f"{INDENT}{mark} ({m['memory_type']}) {m['memory_text']}")
    return response


async def main() -> int:
    await init_db()

    player_id = f"test-{uuid.uuid4()}"
    print(f"Player ID for this run: {player_id}")
    await ash_service.init_player(player_id)

    # ---- Low ash (2): friendly-ish baseline ----------------------------
    _box("PART 1 — ash level 2 (uncorrupted-ish). Three exchanges.")
    await ash_service.set_ash_level(player_id, 2)
    low_1 = await _send(player_id, "Greetings. I need a sword before nightfall.", 2)
    await _send(
        player_id,
        "My name is Aren. I travelled a hundred leagues through the northern waste.",
        2,
    )
    await _send(
        player_id,
        "I lost my brother in the waste. I carry his blade. Can you reforge it?",
        2,
    )

    # ---- High ash (7): should distrust / go cold -----------------------
    _box("PART 2 — ash jumps to 7. Two more exchanges with same player.")
    await ash_service.set_ash_level(player_id, 7)
    high_1 = await _send(
        player_id,
        "Kael. It is me again. I need that sword reforged now.",
        7,
    )
    high_2 = await _send(
        player_id,
        "Do you remember me? I told you about my brother.",
        7,
    )

    # ---- Human-readable verdict ---------------------------------------
    _box("VERDICT")
    print("Compare Kael's tone between the two parts. Expected:")
    print("  - Part 1: curt but fair, engages with the request.")
    print("  - Part 2: refuses or shortens dramatically, may reference Edric.")
    print("  - Kael should reference something the player said earlier.")
    print()
    print("First low-ash reply (trimmed):")
    print(_wrap(low_1[:280]))
    print()
    print("First high-ash reply (trimmed):")
    print(_wrap(high_1[:280]))
    print()
    print("Second high-ash reply (trimmed):")
    print(_wrap(high_2[:280]))
    print()
    print(f"Final memory set for player {player_id} / NPC {NPC_ID}:")
    for m in await get_memories(player_id, NPC_ID):
        mark = "⚠" if m["memory_type"] == "emotional" else "•"
        print(f"{INDENT}{mark} ({m['memory_type']}) {m['memory_text']}")

    print("\nMilestone check complete. Inspect the output above.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
