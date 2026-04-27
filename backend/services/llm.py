import asyncio
import json
import logging
import os
import re

from openai import AsyncOpenAI

log = logging.getLogger(__name__)

MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-5:online")
_client = None

def _get_client():
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        )
    return _client

OUTFIT_SYSTEM_PROMPT = """\
You are an expert personal stylist. Given a client's style profile, generate a complete outfit.

Rules:
- USE YOUR WEB SEARCH to find real, purchasable products with exact product page URLs.
- Return ONLY a valid JSON object, no markdown, no extra text.
- Leave "link" and "image_url" as empty strings — they are found in a separate step.
- Generate 4 pieces: one Top, one Bottom, one Shoes, one Outerwear.
- Each piece must have a specific brand, realistic price, and a brief reason why it suits this person.

Return exactly this structure:
{
  "outfit_concept": "brief concept name",
  "pieces": [
    {"category": "Top", "name": "...", "brand": "...", "price": "$XX", "link": "", "image_url": "", "why": "..."},
    {"category": "Bottom", "name": "...", "brand": "...", "price": "$XX", "link": "", "image_url": "", "why": "..."},
    {"category": "Shoes", "name": "...", "brand": "...", "price": "$XX", "link": "", "image_url": "", "why": "..."},
    {"category": "Outerwear", "name": "...", "brand": "...", "price": "$XX", "link": "", "image_url": "", "why": "..."}
  ]
}"""

URL_SEARCH_PROMPT = """\
USE YOUR WEB SEARCH TOOL RIGHT NOW to find the exact product page for this item.

Brand: {brand}
Item: {name}
Price: {price}

Search for: "{brand} {name} buy online"

Find the real product page URL (not a category page, not a homepage).
Return ONLY this JSON (no markdown):
{{"link": "https://...", "image_url": "https://..."}}

If you cannot find the exact product, return {{"link": "", "image_url": ""}}"""


def _repair_truncated_json(text: str) -> dict | None:
    """Close truncated JSON by tracking brace/bracket depth."""
    try:
        return json.loads(text)
    except Exception:
        pass
    depth = 0
    last_piece_close = -1
    for i, ch in enumerate(text):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 2:
                last_piece_close = i
    if last_piece_close == -1:
        return None
    truncated = text[:last_piece_close + 1]
    candidate = truncated + "]}"
    try:
        return json.loads(candidate)
    except Exception:
        return None


def _build_style_string(profile: dict) -> str:
    gender = profile.get("gender", "")
    style_pref = profile.get("style_pref", "")
    coloring = profile.get("coloring", "")
    undertone = profile.get("undertone", "")
    build = profile.get("build", "")
    hair = profile.get("hair", "")
    return (
        f"Style Profile:\n"
        f"• Gender: {gender}\n"
        f"• Style preference: {style_pref}\n"
        f"• Skin tone: {coloring} with {undertone}\n"
        f"• Body type: {build}\n"
        f"• Hair: {hair}\n\n"
        f"Recommend a complete outfit that flatters and matches this profile."
    )


async def generate_outfit(style_profile: str, previous_outfits: list, feedbacks: list) -> dict:
    client = _get_client()
    messages = [{"role": "user", "content": style_profile}]

    if previous_outfits:
        prev_summary = "; ".join(
            o.get("outfit_concept", "previous outfit") for o in previous_outfits[-3:]
        )
        messages[0]["content"] += f"\n\nAlready shown: {prev_summary}. Generate a distinctly different outfit."

    if feedbacks:
        fb = feedbacks[-1]
        messages[0]["content"] += f"\n\nUser feedback: rating {fb.get('rating')}/5 — {fb.get('text', '')}"

    for attempt in range(3):
        try:
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": OUTFIT_SYSTEM_PROMPT}] + messages,
                max_tokens=2048,
                temperature=0.8,
            )
            raw = resp.choices[0].message.content.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            try:
                return json.loads(raw)
            except Exception:
                repaired = _repair_truncated_json(raw)
                if repaired:
                    return repaired
                log.warning("Attempt %d: invalid JSON, retrying", attempt + 1)
        except Exception as e:
            log.error("Outfit generation attempt %d failed: %s", attempt + 1, e)
            if attempt == 2:
                raise

    raise ValueError("Failed to generate valid outfit JSON after 3 attempts")


async def _find_urls_for_piece(piece: dict) -> dict:
    client = _get_client()
    prompt = URL_SEARCH_PROMPT.format(
        brand=piece.get("brand", ""),
        name=piece.get("name", ""),
        price=piece.get("price", ""),
    )
    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
            temperature=0,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        urls = json.loads(raw)
        if urls.get("link"):
            piece["link"] = urls["link"]
        if urls.get("image_url"):
            piece["image_url"] = urls["image_url"]
    except Exception as e:
        log.warning("URL search failed for '%s': %s", piece.get("name"), e)
    return piece


async def enrich_pieces_with_urls(pieces: list) -> list:
    return list(await asyncio.gather(*[_find_urls_for_piece(p) for p in pieces]))
