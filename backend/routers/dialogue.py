"""All HTTP endpoints. Spec §5.3."""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import JSONResponse

from data.npc_loader import get_npc
from models.request_models import (
    AshUpdateRequest,
    DialogueRequest,
    PlayerInitRequest,
)
from models.response_models import (
    AshUpdateResponse,
    DialogueResponse,
    MemoriesResponse,
    MemoryItem,
    PlayerInitResponse,
    ResetResponse,
)
from services import ash_service, rate_limiter
from services.claude_service import extract_and_store_memory, generate_dialogue
from services.memory_service import (
    delete_all_for_player,
    get_memories,
    insert_dialogue_log,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

DIALOGUE_TIMEOUT_SECONDS = 15


# --------- /api/player/init -------------------------------------------------

@router.post("/player/init", response_model=PlayerInitResponse)
async def player_init(body: PlayerInitRequest) -> PlayerInitResponse:
    result = await ash_service.init_player(body.player_id)
    return PlayerInitResponse(
        player_id=body.player_id,
        ash_level=result["ash_level"],
        is_new=result["is_new"],
    )


# --------- /api/dialogue ----------------------------------------------------

@router.post("/dialogue")
async def dialogue(body: DialogueRequest, background: BackgroundTasks):
    # Rate limit
    if not rate_limiter.allow(body.player_id):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"error": "Please wait before sending another message."},
        )

    # Validate NPC
    npc = get_npc(body.npc_id)
    if npc is None:
        raise HTTPException(status_code=404, detail=f"Unknown npc_id: {body.npc_id}")

    # Accessibility gate
    min_ash = npc.get("min_ash_to_access")
    max_ash = npc.get("max_ash_to_access")
    if min_ash is not None and body.ash_level < min_ash:
        return JSONResponse(
            status_code=403,
            content={
                "error": "npc_unavailable",
                "reason": "You do not see this person.",
            },
        )
    if max_ash is not None and body.ash_level > max_ash:
        reason = npc.get("fallback_response_high_ash") or "This person will not speak with you."
        return JSONResponse(
            status_code=403,
            content={"error": "npc_unavailable", "reason": reason},
        )

    # Ensure player exists in DB
    await ash_service.init_player(body.player_id)

    # Call Claude (with timeout)
    try:
        npc_response = await asyncio.wait_for(
            generate_dialogue(
                npc_id=body.npc_id,
                player_message=body.player_message,
                ash_level=body.ash_level,
                player_id=body.player_id,
            ),
            timeout=DIALOGUE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=200,
            content={
                "npc_response": f"[{npc['name']} stares at you in silence]",
                "npc_id": body.npc_id,
                "memories_updated": False,
                "new_ash_event": None,
                "error": "npc_timeout",
            },
        )
    except Exception:
        logger.exception("Claude dialogue call failed")
        fallback = npc.get("fallback_response_high_ash") or f"[{npc['name']} does not respond]"
        return JSONResponse(
            status_code=200,
            content={
                "npc_response": fallback,
                "npc_id": body.npc_id,
                "memories_updated": False,
                "new_ash_event": None,
                "error": "claude_error",
            },
        )

    # Persist conversation
    await insert_dialogue_log(
        body.player_id, body.npc_id, "player", body.player_message, body.ash_level
    )
    await insert_dialogue_log(
        body.player_id, body.npc_id, "npc", npc_response, body.ash_level
    )

    # Sync ash level from client (client is the source of truth for ash during dialogue)
    await ash_service.set_ash_level(body.player_id, body.ash_level)

    # Fire-and-forget memory extraction
    background.add_task(
        extract_and_store_memory,
        body.player_id,
        body.npc_id,
        body.player_message,
        npc_response,
    )

    return DialogueResponse(
        npc_response=npc_response,
        npc_id=body.npc_id,
        memories_updated=True,
        new_ash_event=None,
    )


# --------- /api/ash/update --------------------------------------------------

@router.post("/ash/update", response_model=AshUpdateResponse)
async def ash_update(body: AshUpdateRequest) -> AshUpdateResponse:
    await ash_service.init_player(body.player_id)
    result = await ash_service.update_ash(body.player_id, body.ash_delta, body.reason)
    return AshUpdateResponse(
        new_ash_level=result["new_ash_level"], capped=result["capped"]
    )


# --------- /api/player/{player_id}/memories/{npc_id} ------------------------

@router.get(
    "/player/{player_id}/memories/{npc_id}",
    response_model=MemoriesResponse,
)
async def get_memories_debug(player_id: str, npc_id: str) -> MemoriesResponse:
    rows = await get_memories(player_id, npc_id)
    return MemoriesResponse(
        memories=[
            MemoryItem(
                memory_text=r["memory_text"],
                memory_type=r["memory_type"],
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]
    )


# --------- /api/player/{player_id}/reset ------------------------------------

@router.delete(
    "/player/{player_id}/reset",
    response_model=ResetResponse,
)
async def reset_player(player_id: str) -> ResetResponse:
    await ash_service.reset_player(player_id)
    await delete_all_for_player(player_id)
    return ResetResponse(reset=True)
