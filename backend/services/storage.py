import json
import os
from datetime import datetime, timezone
from pathlib import Path

OUTFITS_DIR = Path(os.environ.get("OUTFITS_DIR", "./outfits"))


def _session_dir(session_id: str) -> Path:
    return OUTFITS_DIR / session_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session(session_id: str, selfie_path: str, profile: dict) -> dict:
    OUTFITS_DIR.mkdir(parents=True, exist_ok=True)
    _session_dir(session_id).mkdir(parents=True, exist_ok=True)
    session = {
        "session_id": session_id,
        "selfie_path": selfie_path,
        "selfie_url": f"/files/{session_id}/selfie.jpg",
        "profile": profile,
        "outfit": {},
        "tryon_results": {},
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


def update_outfit(session_id: str, outfit: dict) -> dict:
    session = load_session(session_id)
    session["outfit"] = outfit
    _write(session_id, session)
    return session


def save_tryon(session_id: str, item_id: str, image_bytes: bytes) -> str:
    path = _session_dir(session_id) / f"tryon_{item_id}.jpg"
    path.write_bytes(image_bytes)
    url = f"/files/{session_id}/tryon_{item_id}.jpg"
    session = load_session(session_id)
    session["tryon_results"][item_id] = url
    _write(session_id, session)
    return url


def _write(session_id: str, session: dict):
    path = _session_dir(session_id) / "session.json"
    with open(path, "w") as f:
        json.dump(session, f, indent=2)
