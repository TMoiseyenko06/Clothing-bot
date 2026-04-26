from fastapi import APIRouter, HTTPException
from services import storage, logbuffer

router = APIRouter()


@router.get("/logs")
async def get_logs():
    return logbuffer.get_logs()


@router.get("/sessions")
async def list_sessions():
    return storage.list_sessions()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = storage.load_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session
