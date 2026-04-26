import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services import deepfashion, storage

router = APIRouter()
log = logging.getLogger(__name__)


class RefreshPayload(BaseModel):
    session_id: str


class SwapPayload(BaseModel):
    session_id: str
    category: str


@router.post("/outfit/refresh")
async def refresh(payload: RefreshPayload):
    session = storage.load_session(payload.session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    outfit = await deepfashion.search_outfit(session["profile"])
    storage.update_outfit(payload.session_id, outfit)
    return {"outfit": outfit}


@router.post("/outfit/swap")
async def swap(payload: SwapPayload):
    session = storage.load_session(payload.session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    current_id = session["outfit"].get(payload.category, {}).get("id")
    item = await deepfashion.swap_item(session["profile"], payload.category, exclude_id=current_id)
    if not item:
        raise HTTPException(404, f"No more items for {payload.category}")
    outfit = {**session["outfit"], payload.category: item}
    storage.update_outfit(payload.session_id, outfit)
    return {"item": item}
