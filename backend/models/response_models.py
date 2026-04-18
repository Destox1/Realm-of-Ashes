"""Pydantic response schemas (§5 of spec)."""

from typing import Optional

from pydantic import BaseModel


class PlayerInitResponse(BaseModel):
    player_id: str
    ash_level: int
    is_new: bool


class DialogueResponse(BaseModel):
    npc_response: str
    npc_id: str
    memories_updated: bool
    new_ash_event: Optional[dict] = None


class AshUpdateResponse(BaseModel):
    new_ash_level: int
    capped: bool


class MemoryItem(BaseModel):
    memory_text: str
    memory_type: str
    created_at: str


class MemoriesResponse(BaseModel):
    memories: list[MemoryItem]


class ResetResponse(BaseModel):
    reset: bool


class NpcUnavailableResponse(BaseModel):
    error: str = "npc_unavailable"
    reason: str
