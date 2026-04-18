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
