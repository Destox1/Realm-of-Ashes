"""Pydantic request schemas (§5 of spec)."""

from pydantic import BaseModel, Field


class PlayerInitRequest(BaseModel):
    player_id: str = Field(..., min_length=1, max_length=64)


class DialogueRequest(BaseModel):
    player_id: str = Field(..., min_length=1, max_length=64)
    npc_id: str = Field(..., min_length=1, max_length=32)
    player_message: str = Field(..., min_length=1, max_length=200)
    ash_level: int = Field(..., ge=0, le=10)


class AshUpdateRequest(BaseModel):
    player_id: str = Field(..., min_length=1, max_length=64)
    ash_delta: int = Field(..., ge=-10, le=10)
    reason: str = Field(..., min_length=1, max_length=100)
    # Optional: matches an entry in village_service.RUMOR_MAP. When set, this
    # event also enters the village rumour pool and becomes visible to ALL
    # NPCs on their next dialogue. Old clients that don't send this still
    # work (event just doesn't generate a rumour).
    event_type: str | None = Field(default=None, max_length=64)
