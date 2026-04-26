import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from services.llm import analyze_selfie
from services import storage

router = APIRouter()


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")

    content_type = file.content_type or "image/jpeg"
    session_id = str(uuid.uuid4())

    selfie_path = storage.save_selfie(session_id, data)
    style_profile = await analyze_selfie(data, content_type)
    storage.create_session(session_id, selfie_path, style_profile)

    return {"session_id": session_id, "style_profile": style_profile}
