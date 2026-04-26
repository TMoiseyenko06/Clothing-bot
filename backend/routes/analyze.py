import uuid
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from services.llm import analyze_selfie
from services import storage

router = APIRouter()
log = logging.getLogger(__name__)


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")

    content_type = file.content_type or "image/jpeg"
    session_id = str(uuid.uuid4())
    log.info("Analyze request — session=%s content_type=%s size=%d", session_id, content_type, len(data))

    try:
        selfie_path = storage.save_selfie(session_id, data)
        style_profile = await analyze_selfie(data, content_type)
        storage.create_session(session_id, selfie_path, style_profile)
        log.info("Analyze complete — session=%s profile_len=%d", session_id, len(style_profile))
        return {"session_id": session_id, "style_profile": style_profile}
    except Exception as e:
        log.error("Analyze failed — session=%s error=%s", session_id, e, exc_info=True)
        raise HTTPException(500, str(e))
