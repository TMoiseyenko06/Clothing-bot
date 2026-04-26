import os
import logging
import httpx

log = logging.getLogger(__name__)
SERPER_KEY = os.environ.get("SERPER_API_KEY", "")


def _google_shopping_url(brand: str, name: str) -> str:
    q = f"{brand} {name}".replace(" ", "+")
    return f"https://www.google.com/search?tbm=shop&q={q}"


async def enrich_piece(piece: dict) -> dict:
    """
    Add a real product link and image_url to a piece dict.
    Uses Serper Google Shopping if SERPER_API_KEY is set,
    otherwise falls back to a Google Shopping search URL.
    """
    brand = piece.get("brand", "")
    name = piece.get("name", "")
    fallback_link = _google_shopping_url(brand, name)

    if not SERPER_KEY:
        piece["link"] = fallback_link
        piece.setdefault("image_url", "")
        return piece

    query = f"{brand} {name}"
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.post(
                "https://google.serper.dev/shopping",
                headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
                json={"q": query, "num": 3},
            )
            r.raise_for_status()
            results = r.json().get("shopping", [])

        if results:
            top = results[0]
            piece["link"] = top.get("link") or fallback_link
            piece["image_url"] = top.get("imageUrl") or ""
            # Use real price if the LLM left it vague
            if top.get("price") and piece.get("price") in ("", None):
                piece["price"] = top["price"]
            log.info("Serper hit: %s — %s", query, piece["link"])
        else:
            log.warning("Serper returned no results for: %s", query)
            piece["link"] = fallback_link
            piece.setdefault("image_url", "")

    except Exception as e:
        log.warning("Serper search failed for '%s': %s", query, e)
        piece["link"] = fallback_link
        piece.setdefault("image_url", "")

    return piece
