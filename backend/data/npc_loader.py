"""Loads NPC definitions from npcs.json once at import-time."""

import json
from pathlib import Path
from typing import Optional

_NPCS_PATH = Path(__file__).parent / "npcs.json"

with _NPCS_PATH.open(encoding="utf-8") as f:
    _NPC_DATA = json.load(f)

_NPCS_BY_ID = {npc["npc_id"]: npc for npc in _NPC_DATA["npcs"]}


def get_npc(npc_id: str) -> Optional[dict]:
    """Return NPC definition dict by id, or None if not found."""
    return _NPCS_BY_ID.get(npc_id)


def all_npcs() -> list[dict]:
    return list(_NPCS_BY_ID.values())
