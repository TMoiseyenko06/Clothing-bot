import logging
import uuid
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from services import storage
from services import tryon as tryon_svc

router = APIRouter()
log = logging.getLogger(__name__)
OUTFITS_DIR = Path(os.environ.get("OUTFITS_DIR", "./outfits"))


class TryOnPayload(BaseModel):
    session_id: str
    category: str


@router.post("/tryon")
async def run_tryon(payload: TryOnPayload):
    session = storage.load_session(payload.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    outfits = session.get("outfits", [])
    if not outfits:
        raise HTTPException(400, "No outfit generated yet")

    pieces = outfits[-1].get("pieces", [])
    piece = next((p for p in pieces if p.get("category") == payload.category), None)
    if not piece:
        raise HTTPException(404, f"Piece not found: {payload.category}")

    garment_url = piece.get("image_url", "")
    if not garment_url:
        raise HTTPException(400, "No product image for this piece — replace the image first")

    selfie_path = session.get("selfie_path", "")
    if not selfie_path or not Path(selfie_path).exists():
        raise HTTPException(400, "Selfie not found")

    log.info("Try-on — session=%s category=%s", payload.session_id, payload.category)
    try:
        result_path = await tryon_svc.run_tryon(
            payload.session_id,
            selfie_path,
            garment_url,
            payload.category,
        )
    except Exception as e:
        log.error("Try-on failed: %s", e, exc_info=True)
        raise HTTPException(500, str(e))

    rel = Path(result_path).relative_to(OUTFITS_DIR)
    return {"result_url": f"/files/{rel}"}


@router.post("/outfit/update-image")
async def update_piece_image(
    session_id: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(None),
    image_url: str = Form(""),
):
    session = storage.load_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if not session.get("outfits"):
        raise HTTPException(400, "No outfit generated yet")

    if file and file.filename:
        data = await file.read()
        if not data:
            raise HTTPException(400, "Empty file")
        out_dir = OUTFITS_DIR / session_id
        out_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(file.filename).suffix or ".jpg"
        fname = f"garment_{uuid.uuid4().hex[:8]}{suffix}"
        (out_dir / fname).write_bytes(data)
        new_url = f"/files/{session_id}/{fname}"
    elif image_url.strip():
        new_url = image_url.strip()
    else:
        raise HTTPException(400, "Provide either a file upload or image_url")

    storage.update_piece_image(session_id, category, new_url)
    log.info("Image updated — session=%s category=%s url=%s", session_id, category, new_url)
    return {"image_url": new_url, "category": category}
