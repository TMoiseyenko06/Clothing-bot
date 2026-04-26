import os
import json
import httpx
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
        "style_profile": style_profile,
        "onboarding": None,
        "outfits": [],
        "feedbacks": [],
        "created_at": _now(),
        "updated_at": _now(),
    }
    _write_session(session_id, session)
    return session


def load_session(session_id: str) -> dict | None:
    path = _session_dir(session_id) / "session.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _write_session(session_id: str, session: dict):
    path = _session_dir(session_id) / "session.json"
    with open(path, "w") as f:
        json.dump(session, f, indent=2)


def save_selfie(session_id: str, data: bytes) -> str:
    d = _session_dir(session_id)
    d.mkdir(parents=True, exist_ok=True)
    path = d / "selfie.jpg"
    with open(path, "wb") as f:
        f.write(data)
    return str(path)


def update_onboarding(session_id: str, onboarding: dict):
    session = load_session(session_id)
    session["onboarding"] = onboarding
    session["updated_at"] = _now()
    _write_session(session_id, session)


def save_outfit(session_id: str, outfit: dict, feedback: dict | None) -> dict:
    session = load_session(session_id)
    outfit_index = len(session["outfits"]) + 1

    cache_dir = _session_dir(session_id) / "cached_images"
    cache_dir.mkdir(exist_ok=True)

    for i, piece in enumerate(outfit.get("pieces", [])):
        cached = _cache_image(piece.get("image_url", ""), cache_dir, i + 1)
        if cached:
            piece["cached_image"] = f"/files/{session_id}/cached_images/{cached.name}"

    outfit_path = _session_dir(session_id) / f"outfit_{outfit_index}.json"
    with open(outfit_path, "w") as f:
        json.dump(outfit, f, indent=2)

    session["outfits"].append(outfit)
    if feedback:
        session["feedbacks"].append(feedback)
    session["updated_at"] = _now()
    _write_session(session_id, session)
    return session


def _cache_image(url: str, cache_dir: Path, index: int) -> Path | None:
    if not url:
        return None
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            r = client.get(url)
            if r.status_code == 200:
                path = cache_dir / f"piece_{index}.jpg"
                with open(path, "wb") as f:
                    f.write(r.content)
                return path
    except Exception:
        pass
    return None


def list_sessions() -> list:
    if not OUTFITS_DIR.exists():
        return []
    sessions = []
    for d in sorted(OUTFITS_DIR.iterdir(), reverse=True):
        if d.is_dir():
            session_file = d / "session.json"
            if session_file.exists():
                with open(session_file) as f:
                    sessions.append(json.load(f))
    return sessions
