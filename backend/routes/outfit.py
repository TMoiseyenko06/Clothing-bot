import asyncio
import logging
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.llm import generate_outfit, enrich_pieces_with_urls
from services import storage

router = APIRouter()
log = logging.getLogger(__name__)

_BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


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


async def _verify_piece(piece: dict, session_id: str, index: int) -> dict | None:
    """
    Verify a piece has a working product link AND a downloadable image.
    Returns the enriched piece (with cached_image set) or None if either check fails.
    Pieces that fail are dropped from the outfit entirely — no fallbacks.
    """
    name = piece.get("name", "?")
    link = piece.get("link", "").strip()
    image_url = piece.get("image_url", "").strip()

    if not link:
        log.warning("DROP '%s' — no product link returned", name)
        return None

    if not image_url:
        log.warning("DROP '%s' — no image URL returned", name)
        return None

    # Validate the product link
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            r = await client.head(link, headers=_BROWSER_UA)
        if r.status_code >= 400:
            log.warning("DROP '%s' — link returned HTTP %d: %s", name, r.status_code, link)
            return None
        log.info("LINK OK (%d) '%s': %s", r.status_code, name, link)
    except Exception as e:
        log.warning("DROP '%s' — link check error: %s", name, e)
        return None

    # Download and cache the image — piece is dropped if image can't be fetched
    cached_url = await asyncio.to_thread(storage.try_cache_image, session_id, image_url, index)
    if not cached_url:
        log.warning("DROP '%s' — image could not be downloaded: %s", name, image_url)
        return None

    piece["cached_image"] = cached_url
    log.info("IMAGE OK '%s': cached at %s", name, cached_url)
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
        log.info("Outfit generated — concept='%s' candidates=%d",
                 outfit.get("outfit_concept", "?"), len(outfit.get("pieces", [])))
    except Exception as e:
        log.error("Outfit generation failed — session=%s error=%s", payload.session_id, e, exc_info=True)
        raise HTTPException(500, str(e))

    # Dedicated per-piece search for exact product URL + image
    log.info("Searching for exact product URLs for %d pieces...", len(outfit.get("pieces", [])))
    outfit["pieces"] = await enrich_pieces_with_urls(outfit.get("pieces", []))

    # Verify each piece: working link + downloadable image required — drop failures
    results = await asyncio.gather(*[
        _verify_piece(p, payload.session_id, i + 1)
        for i, p in enumerate(outfit.get("pieces", []))
    ])
    verified = [p for p in results if p is not None]

    log.info("Verified %d/%d pieces with working links and images",
             len(verified), len(outfit.get("pieces", [])))

    if not verified:
        raise HTTPException(500, "No pieces with verified links and images could be found. Please try again.")

    outfit["pieces"] = verified

    updated_session = await asyncio.to_thread(
        storage.save_outfit, payload.session_id, outfit, feedback_dict
    )

    saved_outfit = updated_session["outfits"][-1]
    return {"outfit": saved_outfit, "outfit_index": len(updated_session["outfits"])}
