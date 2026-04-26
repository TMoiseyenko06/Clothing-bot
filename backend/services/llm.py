import os
import json
import re
import asyncio
import base64
import logging
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
    base_url="https://openrouter.ai/api/v1",
)

MODEL = "google/gemini-2.5-pro:online"
log = logging.getLogger(__name__)

OUTFIT_SYSTEM_PROMPT = """You are an expert personal stylist. Your job is to build a complete,
cohesive outfit for a real person based on their style profile,
stated preferences, and any feedback from previous outfit attempts.

ALWAYS return a JSON object only — no markdown, no preamble, no
explanation outside the JSON. The JSON must match this exact schema:

{
  "outfit_concept": "string — brief description of the overall vibe",
  "pieces": [
    {
      "category": "Top | Bottom | Shoes | Outerwear | Accessory",
      "name": "string — specific product name",
      "brand": "string — real brand name",
      "price": "string — approximate retail price e.g. $89",
      "link": "",
      "image_url": "",
      "why": "string — one short sentence (under 15 words) why this works for this person"
    }
  ]
}

Rules:
- Choose real brands and specific product names that exist and are available online
- All pieces must work together cohesively as a complete outfit
- Respect the user's budget range strictly
- Incorporate feedback from previous iterations — do not repeat rejected pieces
- Always include at minimum: Top, Bottom, Shoes
- First decide the full outfit concept, then choose pieces that match it
- Leave "link" and "image_url" as empty strings — they are found separately"""

URL_SEARCH_PROMPT = """Search the web for this exact clothing item and find its product page.

Brand: {brand}
Item name: {name}
Approx price: {price}

Steps you must follow:
1. Search for "{brand} {name} buy" on the web
2. Find the listing on the brand's own website OR a major retailer (Nordstrom, ASOS, Zappos, etc.)
3. Click through to the specific individual product page — the page must show ONLY this one item
4. Confirm the page has an Add to Cart or Buy button
5. Find the main product image URL directly from the page (a CDN/static image URL)

Return ONLY this raw JSON — no markdown, no explanation:
{{"link": "<exact product page URL>", "image_url": "<direct image URL ending in .jpg .png or .webp>"}}

If you cannot find the exact individual product page, return:
{{"link": "", "image_url": ""}}"""


def _clean_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _repair_truncated_json(text: str) -> dict | None:
    """Salvage a truncated JSON response by closing the last complete piece."""
    depth = 0
    in_string = False
    escape_next = False
    last_piece_end = -1

    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue

        prev = depth
        if ch in ("{", "["):
            depth += 1
        elif ch in ("}", "]"):
            depth -= 1
            if prev == 3 and depth == 2:
                last_piece_end = i

    if last_piece_end < 0:
        return None

    partial = text[: last_piece_end + 1].rstrip().rstrip(",")
    candidate = partial + "\n  ]\n}"
    try:
        result = json.loads(candidate)
        log.warning("Repaired truncated JSON — kept %d piece(s)", len(result.get("pieces", [])))
        return result
    except json.JSONDecodeError:
        return None


async def _find_urls_for_piece(piece: dict) -> dict:
    """Dedicated per-piece search call to find the exact product URL and image."""
    prompt = URL_SEARCH_PROMPT.format(
        brand=piece.get("brand", ""),
        name=piece.get("name", ""),
        price=piece.get("price", ""),
    )
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
        )
        raw = response.choices[0].message.content
        data = json.loads(_clean_json(raw))
        if data.get("link"):
            piece["link"] = data["link"]
            log.info("URL found for '%s %s': %s", piece.get("brand"), piece.get("name"), data["link"])
        if data.get("image_url"):
            piece["image_url"] = data["image_url"]
    except Exception as e:
        log.warning("URL search failed for '%s %s': %s", piece.get("brand"), piece.get("name"), e)
    return piece


async def enrich_pieces_with_urls(pieces: list) -> list:
    """Run one dedicated URL-search call per piece, all in parallel."""
    return list(await asyncio.gather(*[_find_urls_for_piece(p) for p in pieces]))


async def analyze_selfie(image_bytes: bytes, content_type: str) -> str:
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{content_type};base64,{image_data}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Analyze the attached photo. Describe the person's skin tone, coloring "
                            "(warm/cool/neutral), apparent body proportions, and any visible style cues. "
                            "Output a concise style profile that will be used to generate clothing "
                            "recommendations. Be specific and practical."
                        ),
                    },
                ],
            }
        ],
        max_tokens=1024,
    )
    return response.choices[0].message.content


async def generate_outfit(
    style_profile: str,
    onboarding: dict,
    previous_outfits: list,
    feedbacks: list,
) -> dict:
    pref_str = (
        f"Gender preference: {onboarding.get('gender', 'Not specified')}\n"
        f"Fit preference: {onboarding.get('fit', 'Not specified')}\n"
        f"Budget: {onboarding.get('budget', 'Not specified')}\n"
        f"Occasion: {onboarding.get('occasion', 'Not specified')}"
    )

    if previous_outfits:
        history_parts = []
        for i, (outfit, feedback) in enumerate(zip(previous_outfits, feedbacks), 1):
            concept = outfit.get("outfit_concept", "")
            pieces_str = ", ".join(
                f"{p.get('name')} by {p.get('brand')}" for p in outfit.get("pieces", [])
            )
            fb_rating = feedback.get("rating", "") if feedback else ""
            fb_text = feedback.get("text", "") if feedback else ""
            history_parts.append(
                f"Outfit {i} (rated {fb_rating}/5): {concept}\n"
                f"Pieces: {pieces_str}\n"
                f"Feedback: {fb_text}"
            )
        history_str = "\n\n".join(history_parts)
        user_content = (
            f"Style profile: {style_profile}\n\n"
            f"Preferences:\n{pref_str}\n\n"
            f"Previous outfits and feedback:\n{history_str}\n\n"
            "Build a new outfit that addresses the feedback and improves on the previous attempts."
        )
    else:
        user_content = (
            f"Style profile: {style_profile}\n\n"
            f"Preferences:\n{pref_str}\n\n"
            "Build a cohesive outfit for this person based on their style profile and preferences."
        )

    for attempt in range(2):
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": OUTFIT_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=4096,
        )
        raw = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason
        cleaned = _clean_json(raw)

        if finish_reason == "length":
            log.warning("Response truncated (finish_reason=length) on attempt %d", attempt + 1)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        repaired = _repair_truncated_json(cleaned)
        if repaired and repaired.get("pieces"):
            return repaired

        if attempt == 0:
            user_content += (
                "\n\nIMPORTANT: Return ONLY the raw JSON object. "
                "No markdown, no text outside the JSON. Keep all string values concise."
            )
            continue

        raise ValueError(f"LLM returned invalid JSON after retry: {raw[:300]}")
