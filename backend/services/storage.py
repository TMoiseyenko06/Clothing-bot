import json
import os
from datetime import datetime, timezone
from pathlib import Path

OUTFITS_DIR = Path(os.environ.get("OUTFITS_DIR", "./outfits"))


def _session_dir(session_id: str) -> Path:
    return OUTFITS_DIR / session_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session(session_id: str, selfie_path: str, style_profile: str) -> dict:
    OUTFITS_DIR.mkdir(parents=True, exist_ok=True)
    _session_dir(session_id).mkdir(parents=True, exist_ok=True)
    session = {
        "session_id": session_id,
        "selfie_path": selfie_path,
        "selfie_url": f"/files/{session_id}/selfie.jpg",
        "style_profile": style_profile,
        "outfits": [],
        "feedbacks": [],
        "created_at": _now(),
    }
    _write(session_id, session)
    return session


def load_session(session_id: str) -> dict | None:
    path = _session_dir(session_id) / "session.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def save_selfie(session_id: str, data: bytes) -> str:
    d = _session_dir(session_id)
    d.mkdir(parents=True, exist_ok=True)
    path = d / "selfie.jpg"
    path.write_bytes(data)
    return str(path)


def save_outfit(session_id: str, outfit: dict, feedback: dict | None) -> dict:
    session = load_session(session_id)
    session["outfits"].append(outfit)
    if feedback:
        session["feedbacks"].append(feedback)
    _write(session_id, session)
    return session


def _write(session_id: str, session: dict):
    path = _session_dir(session_id) / "session.json"
    with open(path, "w") as f:
        json.dump(session, f, indent=2)
