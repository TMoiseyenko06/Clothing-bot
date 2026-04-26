import asyncio
import logging
from urllib.parse import quote_plus
import httpx
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


def _shopping_fallback(brand: str, name: str) -> str:
    return f"https://www.google.com/search?tbm=shop&q={quote_plus(brand + ' ' + name)}"


async def _validate_piece(piece: dict) -> dict:
    """HEAD-check the link; replace broken ones with a Google Shopping search."""
    brand = piece.get("brand", "")
    name = piece.get("name", "")
    link = piece.get("link", "").strip()

    if not link:
        piece["link"] = _shopping_fallback(brand, name)
        log.info("No link for '%s' — using Google Shopping fallback", name)
        return piece

    try:
        async with httpx.AsyncClient(timeout=6, follow_redirects=True) as client:
            r = await client.head(link, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code >= 400:
            log.warning("Link %s returned %d for '%s' — using fallback", link, r.status_code, name)
            piece["link"] = _shopping_fallback(brand, name)
        else:
            log.info("Link OK (%d): %s", r.status_code, link)
    except Exception as e:
        log.warning("Link check failed for '%s' (%s) — using fallback", name, e)
        piece["link"] = _shopping_fallback(brand, name)

    return piece


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

    # Step 2: dedicated per-piece search for exact product URL + image
    log.info("Searching for exact product URLs for %d pieces...", len(outfit.get("pieces", [])))
    outfit["pieces"] = await enrich_pieces_with_urls(outfit.get("pieces", []))

    # Step 3: validate links; replace any still-broken ones with Google Shopping fallback
    outfit["pieces"] = list(
        await asyncio.gather(*[_validate_piece(p) for p in outfit.get("pieces", [])])
    )

    updated_session = await asyncio.to_thread(
        storage.save_outfit, payload.session_id, outfit, feedback_dict
    )

    return {"outfit": outfit, "outfit_index": len(updated_session["outfits"])}
