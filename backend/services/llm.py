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
You are an expert personal stylist. Your job has TWO parts:

PART 1 — Design the outfit:
Create a cohesive outfit concept for the client based on their style profile.
Choose REAL, currently-sold products from well-known brands (e.g. Levi's, Zara, Nike, Mango, ASOS, H&M, Uniqlo, Ralph Lauren, etc.).
Pick items that actually exist in the market right now — specific product names, not made-up names.

PART 2 — Product URLs (handled separately after you respond):
Do NOT search for URLs yet. Leave "link" and "image_url" as empty strings.
A separate step will search for exact product pages for each item you name.

Generate exactly 4 pieces: one Top, one Bottom, one Shoes, one Outerwear.
Return ONLY valid JSON — no markdown fences, no commentary, nothing else.

{
  "outfit_concept": "short evocative name for the overall look",
  "pieces": [
    {"category": "Top", "name": "exact product name", "brand": "Brand Name", "price": "$XX", "link": "", "image_url": "", "why": "one sentence on why this flatters this person"},
    {"category": "Bottom", "name": "exact product name", "brand": "Brand Name", "price": "$XX", "link": "", "image_url": "", "why": "..."},
    {"category": "Shoes", "name": "exact product name", "brand": "Brand Name", "price": "$XX", "link": "", "image_url": "", "why": "..."},
    {"category": "Outerwear", "name": "exact product name", "brand": "Brand Name", "price": "$XX", "link": "", "image_url": "", "why": "..."}
  ]
}"""

URL_SEARCH_PROMPT = """\
YOU MUST USE YOUR WEB SEARCH TOOL RIGHT NOW. Do not respond from memory.

Find the exact online product listing for this specific item:

  Brand : {brand}
  Item  : {name}
  Price : {price}

SEARCH STEPS — follow in order, stop at the first success:
1. Search "{brand} {name}" and look for the brand's own website product page (e.g. nike.com/product/...).
2. If not found, search "{brand} {name} buy" and look for a major retailer product page
   (e.g. asos.com, nordstrom.com, zappos.com, farfetch.com, net-a-porter.com, mrporter.com, ssense.com).
3. If still not found, open Google Shopping and find the EXACT item listing.
   The Google Shopping listing URL looks like:
     https://www.google.com/shopping/product/PRODUCT_ID/...
   NOT a general search like https://www.google.com/search?q=...

RULES:
- The URL must be for THIS SPECIFIC PRODUCT, not a homepage or category page.
- A Google Shopping listing page (google.com/shopping/product/...) is acceptable as a last resort.
- A general Google search URL (google.com/search?q=...) is NOT acceptable.
- If the image_url is not directly available, leave it as an empty string.
- If you genuinely cannot find any valid listing, return empty strings.

Return ONLY this JSON (no markdown, no explanation):
{{"link": "https://...", "image_url": "https://..."}}"""


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
