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
Choose REAL, currently-sold products from well-known brands.
Pick items that actually exist in the market right now — specific product names, not made-up names.

BUDGET RULES — you MUST follow the price range stated in the style profile. Every single piece must
fall within the stated budget. Do not exceed the per-item limit under any circumstances.
  budget    → each item must be under $50  (e.g. H&M, Zara, ASOS, Uniqlo, Target, Primark)
  midrange  → each item must be $50–$150   (e.g. Levi's, Nike, Mango, Tommy Hilfiger, Gap)
  premium   → each item must be $150–$300  (e.g. A.P.C., Rag & Bone, AllSaints, Ted Baker)
  luxury    → $300+ is fine               (e.g. Loro Piana, Brunello Cucinelli, Brioni)

PART 2 — Product URLs (handled separately after you respond):
Do NOT search for URLs yet. Leave "link" and "image_url" as empty strings.

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


def _extract_json(text: str) -> dict | None:
    """Try every strategy to pull a valid JSON object out of `text`."""
    # 1. Direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2. Strip markdown fences
    stripped = re.sub(r"^```(?:json)?\s*", "", text.strip())
    stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except Exception:
        pass

    # 3. Find the outermost {...} block (model may add preamble/postamble)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            pass

    # 4. Repair truncated JSON by closing at the last complete piece
    depth = 0
    last_piece_close = -1
    for i, ch in enumerate(text):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 2:
                last_piece_close = i
    if last_piece_close != -1:
        try:
            return json.loads(text[:last_piece_close + 1] + "]}")
        except Exception:
            pass

    return None


_BUDGET_LABELS = {
    "budget":   "Budget — every item must be under $50",
    "midrange": "Mid-range — every item must be $50–$150",
    "premium":  "Premium — every item must be $150–$300",
    "luxury":   "Luxury — $300+ per item is fine",
}


def _build_style_string(profile: dict) -> str:
    budget_key = profile.get("budget", "midrange")
    budget_line = _BUDGET_LABELS.get(budget_key, _BUDGET_LABELS["midrange"])
    return (
        f"Style Profile:\n"
        f"• Gender: {profile.get('gender', '')}\n"
        f"• Style preference: {profile.get('style_pref', '')}\n"
        f"• Budget: {budget_line}\n"
        f"• Skin tone: {profile.get('coloring', '')} with {profile.get('undertone', '')}\n"
        f"• Body type: {profile.get('build', '')}\n"
        f"• Hair: {profile.get('hair', '')}\n\n"
        f"Recommend a complete outfit that flatters and matches this profile. "
        f"Strictly respect the budget — do not suggest items outside the stated price range."
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
                max_tokens=3000,
                temperature=0.8,
            )
            choice = resp.choices[0]
            raw = (choice.message.content or "").strip()

            # The :online model sometimes returns content via tool_calls rather than
            # message.content; collect any text parts from tool_call results too.
            if not raw and hasattr(choice.message, "tool_calls") and choice.message.tool_calls:
                parts = []
                for tc in choice.message.tool_calls:
                    if hasattr(tc, "function") and tc.function.arguments:
                        parts.append(tc.function.arguments)
                raw = " ".join(parts)

            log.debug("Attempt %d raw response (%d chars): %.500s", attempt + 1, len(raw), raw)

            if not raw:
                log.warning("Attempt %d: empty response from model", attempt + 1)
                continue

            result = _extract_json(raw)
            if result and result.get("pieces"):
                return result

            log.warning("Attempt %d: could not extract valid outfit JSON. Raw snippet: %.300s", attempt + 1, raw)
        except Exception as e:
            log.error("Outfit generation attempt %d failed: %s", attempt + 1, e, exc_info=True)
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
            max_tokens=512,
            temperature=0,
        )
        raw = (resp.choices[0].message.content or "").strip()
        log.debug("URL search raw for '%s': %.300s", piece.get("name"), raw)
        urls = _extract_json(raw) or {}
        link = urls.get("link", "")
        image_url = urls.get("image_url", "")
        # Reject bare search URLs — only accept direct product or Shopping listing pages
        if link and "google.com/search" not in link:
            piece["link"] = link
        if image_url:
            piece["image_url"] = image_url
    except Exception as e:
        log.warning("URL search failed for '%s': %s", piece.get("name"), e)
    return piece


async def enrich_pieces_with_urls(pieces: list) -> list:
    return list(await asyncio.gather(*[_find_urls_for_piece(p) for p in pieces]))
