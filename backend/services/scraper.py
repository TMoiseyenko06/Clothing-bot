import logging
import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


async def scrape_product_image(url: str) -> str | None:
    """
    Fetch a product page and extract the main product image URL.
    Tries in order: og:image → twitter:image → first large <img> with a CDN src.
    Returns None if nothing usable is found.
    """
    if not url:
        return None
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            r = await client.get(url, headers=_HEADERS)
        if r.status_code != 200:
            log.warning("Scrape failed for %s — HTTP %d", url, r.status_code)
            return None

        soup = BeautifulSoup(r.text, "html.parser")

        # og:image is the most reliable — set by virtually every e-commerce site
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            img = og["content"].strip()
            log.info("Scraped og:image from %s: %s", url, img)
            return img

        # twitter:image as secondary
        tw = soup.find("meta", attrs={"name": "twitter:image"})
        if tw and tw.get("content"):
            img = tw["content"].strip()
            log.info("Scraped twitter:image from %s: %s", url, img)
            return img

        # Last resort: first <img> whose src looks like a CDN product image
        for img_tag in soup.find_all("img", src=True):
            src = img_tag["src"]
            if any(src.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
                if any(kw in src for kw in ("product", "item", "cdn", "media", "image", "img")):
                    log.info("Scraped <img> src from %s: %s", url, src)
                    return src if src.startswith("http") else None

    except Exception as e:
        log.warning("Scrape error for %s: %s", url, e)

    return None
