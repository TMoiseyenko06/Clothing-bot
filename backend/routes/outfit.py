import asyncio
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.llm import generate_outfit, enrich_pieces_with_urls
from services import storage

router = APIRouter()
log = logging.getLogger(__name__)


class OnboardingPayload(BaseModel):
    gender: str
    fit: str
    budget: str
    occasion: str


class FeedbackPayload(BaseModel):
    rating: int
    text: str


class GeneratePayload(BaseModel):
    session_id: str
    onboarding: Optional[OnboardingPayload] = None
    feedback: Optional[FeedbackPayload] = None


@router.post("/outfit/generate")
async def generate(payload: GeneratePayload):
    session = storage.load_session(payload.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    if payload.onboarding:
        storage.update_onboarding(payload.session_id, payload.onboarding.model_dump())
        session["onboarding"] = payload.onboarding.model_dump()

    onboarding = session.get("onboarding") or {}
    feedback_dict = payload.feedback.model_dump() if payload.feedback else None

    existing_feedbacks = session.get("feedbacks", [])
    feedbacks_for_generation = existing_feedbacks + ([feedback_dict] if feedback_dict else [])
    iteration = len(session.get("outfits", [])) + 1

    log.info("Generating outfit #%d — session=%s", iteration, payload.session_id)

    try:
        outfit = await generate_outfit(
            style_profile=session["style_profile"],
            onboarding=onboarding,
            previous_outfits=session.get("outfits", []),
            feedbacks=feedbacks_for_generation,
        )
        log.info("Outfit generated — concept='%s' pieces=%d",
                 outfit.get("outfit_concept", "?"), len(outfit.get("pieces", [])))
    except Exception as e:
        log.error("Outfit generation failed — session=%s error=%s", payload.session_id, e, exc_info=True)
        raise HTTPException(500, str(e))

    # Per-piece search for exact product URL + image
    outfit["pieces"] = await enrich_pieces_with_urls(outfit.get("pieces", []))

    updated_session = await asyncio.to_thread(
        storage.save_outfit, payload.session_id, outfit, feedback_dict
    )

    saved_outfit = updated_session["outfits"][-1]
    return {"outfit": saved_outfit, "outfit_index": len(updated_session["outfits"])}
