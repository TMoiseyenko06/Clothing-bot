import asyncio
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.llm import generate_outfit, enrich_pieces_with_urls
from services.scraper import scrape_product_image
from services import storage

router = APIRouter()
log = logging.getLogger(__name__)


class FeedbackPayload(BaseModel):
    rating: int
    text: str


class GeneratePayload(BaseModel):
    session_id: str
    feedback: Optional[FeedbackPayload] = None


async def _fill_missing_image(piece: dict) -> dict:
    if piece.get("image_url") or not piece.get("link"):
        return piece
    img = await scrape_product_image(piece["link"])
    if img:
        piece["image_url"] = img
        log.info("Scraped image for '%s'", piece.get("name"))
    return piece


@router.post("/outfit/generate")
async def generate(payload: GeneratePayload):
    session = storage.load_session(payload.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    feedback_dict = payload.feedback.model_dump() if payload.feedback else None
    existing_feedbacks = session.get("feedbacks", [])
    feedbacks_for_gen = existing_feedbacks + ([feedback_dict] if feedback_dict else [])

    log.info("Generating outfit — session=%s iteration=%d", payload.session_id, len(session.get("outfits", [])) + 1)

    try:
        outfit = await generate_outfit(
            style_profile=session["style_profile"],
            previous_outfits=session.get("outfits", []),
            feedbacks=feedbacks_for_gen,
        )
        log.info("Outfit concept: %s, pieces: %d", outfit.get("outfit_concept"), len(outfit.get("pieces", [])))
    except Exception as e:
        log.error("Outfit generation failed: %s", e, exc_info=True)
        raise HTTPException(500, str(e))

    outfit["pieces"] = await enrich_pieces_with_urls(outfit.get("pieces", []))
    outfit["pieces"] = list(await asyncio.gather(*[_fill_missing_image(p) for p in outfit["pieces"]]))

    updated = storage.save_outfit(payload.session_id, outfit, feedback_dict)
    saved_outfit = updated["outfits"][-1]
    return {"outfit": saved_outfit, "outfit_index": len(updated["outfits"])}
