import asyncio
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.llm import generate_outfit
from services.search import enrich_piece
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
        log.info("Outfit #%d generated — concept=%s pieces=%d",
                 iteration, outfit.get("outfit_concept", "?"), len(outfit.get("pieces", [])))
    except Exception as e:
        log.error("Outfit generation failed — session=%s iteration=%d error=%s",
                  payload.session_id, iteration, e, exc_info=True)
        raise HTTPException(500, str(e))

    # Enrich all pieces with real product links + images in parallel
    try:
        enriched = await asyncio.gather(*[enrich_piece(p) for p in outfit.get("pieces", [])])
        outfit["pieces"] = list(enriched)
        log.info("Enriched %d pieces with real product data", len(enriched))
    except Exception as e:
        log.warning("Product enrichment partially failed: %s", e)

    updated_session = await asyncio.to_thread(
        storage.save_outfit, payload.session_id, outfit, feedback_dict
    )

    return {"outfit": outfit, "outfit_index": len(updated_session["outfits"])}
