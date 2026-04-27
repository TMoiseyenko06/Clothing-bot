import uuid
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from services import fashionclip, deepfashion, storage

router = APIRouter()
log = logging.getLogger(__name__)


@router.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    gender: str = Form("unisex"),
    style_pref: str = Form("casual"),
):
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")

    session_id = str(uuid.uuid4())
    log.info("Analyze — session=%s size=%d gender=%s style=%s", session_id, len(data), gender, style_pref)

    try:
        selfie_path = storage.save_selfie(session_id, data)
        profile = await fashionclip.analyze_selfie(data)
        profile["gender"] = gender
        profile["style_pref"] = style_pref
        log.info("Profile — %s", profile)

        outfit = await deepfashion.search_outfit(profile)
        log.info("Outfit — categories=%s", list(outfit.keys()))

        session = storage.create_session(session_id, selfie_path, profile)
        storage.update_outfit(session_id, outfit)

        return {
            "session_id": session_id,
            "profile": profile,
            "outfit": outfit,
            "selfie_url": session["selfie_url"],
        }
    except Exception as e:
        log.error("Analyze failed — %s", e, exc_info=True)
        raise HTTPException(500, str(e))
