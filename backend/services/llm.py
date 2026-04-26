import os
import json
import re
import base64
import logging
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
    base_url="https://openrouter.ai/api/v1",
)

MODEL = "google/gemini-2.5-pro"
log = logging.getLogger(__name__)

OUTFIT_SYSTEM_PROMPT = """You are an expert personal stylist. Your job is to build a complete,
cohesive outfit for a real person based on their style profile,
stated preferences, and any feedback from previous outfit attempts.

Use your web search capability to find real, currently available,
purchasable clothing items with working product links and images.

ALWAYS return a JSON object only — no markdown, no preamble, no
explanation outside the JSON. The JSON must match this exact schema:

{
  "outfit_concept": "string — brief description of the overall vibe",
  "pieces": [
    {
      "category": "Top | Bottom | Shoes | Outerwear | Accessory",
      "name": "string",
      "brand": "string",
      "price": "string",
      "link": "string — direct product URL",
      "image_url": "string — direct image URL",
      "why": "string — one sentence explaining why this works for this person"
    }
  ]
}

Rules:
- Every piece must be real and currently purchasable
- All pieces must work together cohesively as a complete outfit
- Respect the user's budget range strictly
- Incorporate feedback from previous iterations — do not repeat rejected pieces
- Always include at minimum: Top, Bottom, Shoes
- First decide the full outfit concept, then find pieces that match it
- Keep each "why" field to one short sentence (under 15 words)"""


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
    last_piece_end = -1  # char index where depth last fell back to 2 (piece closed)

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
            # depth 3→2 means a piece object just closed inside the pieces array
            if prev == 3 and depth == 2:
                last_piece_end = i

    if last_piece_end < 0:
        return None

    # Strip trailing comma after the last complete piece, then close the structure
    partial = text[: last_piece_end + 1].rstrip().rstrip(",")
    candidate = partial + "\n  ]\n}"
    try:
        result = json.loads(candidate)
        log.warning("Repaired truncated JSON — kept %d piece(s)", len(result.get("pieces", [])))
        return result
    except json.JSONDecodeError:
        return None


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

        # Try clean parse first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try to repair a truncated response before retrying
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
