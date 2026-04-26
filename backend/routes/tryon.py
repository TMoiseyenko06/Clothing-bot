import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services import storage, tryon
from services.deepfashion import get_item_image_path

router = APIRouter()
log = logging.getLogger(__name__)


class TryOnPayload(BaseModel):
    session_id: str
    item_id: str
    category: str


@router.post("/tryon")
async def generate_tryon(payload: TryOnPayload):
    session = storage.load_session(payload.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    selfie_path = Path(session["selfie_path"])
    if not selfie_path.exists():
        raise HTTPException(404, "Selfie not found")
    person_bytes = selfie_path.read_bytes()

    garment_path = get_item_image_path(payload.item_id)
    if not garment_path:
        raise HTTPException(404, f"Garment image not found for item {payload.item_id}")
    garment_bytes = garment_path.read_bytes()

    log.info("Try-on — session=%s item=%s category=%s", payload.session_id, payload.item_id, payload.category)

    try:
        result_bytes = await tryon.generate(person_bytes, garment_bytes, payload.category)
        result_url = storage.save_tryon(payload.session_id, payload.item_id, result_bytes)
        return {"result_url": result_url}
    except Exception as e:
        log.error("Try-on failed — %s", e, exc_info=True)
        raise HTTPException(500, str(e))
