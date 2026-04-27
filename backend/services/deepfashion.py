import asyncio
import json
import logging
import os
from pathlib import Path
import numpy as np

log = logging.getLogger(__name__)

CATALOG_DIR = Path(os.environ.get("CATALOG_DIR", "./catalog"))
_INDEX_FILE = CATALOG_DIR / "faiss.index"
_META_FILE = CATALOG_DIR / "metadata.json"
MAX_ITEMS = int(os.environ.get("CATALOG_MAX_ITEMS", "0"))

_index = None
_meta = None
_load_lock = asyncio.Lock()


async def _ensure_loaded():
    global _index, _meta
    if _index is not None:
        return
    async with _load_lock:
        if _index is not None:
            return
        if _INDEX_FILE.exists() and _META_FILE.exists():
            log.info("Loading catalog index from disk...")
            await asyncio.to_thread(_load_from_disk)
        else:
            log.info("Building catalog index — first run may take several minutes...")
            await asyncio.to_thread(_build_index)


def _load_from_disk():
    global _index, _meta
    import faiss
    _index = faiss.read_index(str(_INDEX_FILE))
    with open(_META_FILE) as f:
        _meta = json.load(f)
    log.info("Loaded %d items from catalog index", len(_meta))


def _build_index():
    global _index, _meta
    import faiss
    from datasets import load_dataset
    from services.fashionclip import embed_images_batch, embed_text

    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    images_dir = CATALOG_DIR / "images"
    images_dir.mkdir(exist_ok=True)

    log.info("Downloading nreimers/fashion-dataset...")
    ds = load_dataset("nreimers/fashion-dataset", split="train")

    cols = ds.column_names
    log.info("Dataset columns: %s", cols)
    log.info("Sample row: %s", {k: str(ds[0][k])[:80] for k in cols})

    total = len(ds)
    if MAX_ITEMS and MAX_ITEMS < total:
        total = MAX_ITEMS
        ds = ds.select(range(total))

    log.info("Indexing %d items...", total)

    has_images = "image" in cols

    # Detect field names flexibly
    desc_col  = next((c for c in ["description", "name", "title", "text", "productDisplayName"] if c in cols), None)
    cat_col   = next((c for c in ["category", "articleType", "subCategory", "label", "type"] if c in cols), None)
    gender_col = next((c for c in ["gender", "Gender"] if c in cols), None)
    img_url_col = next((c for c in ["image_url", "imageUrl", "img_url", "url"] if c in cols), None)

    meta = []
    all_embeddings = []
    batch_size = 32

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = ds[start:end]
        n = end - start

        descs   = batch[desc_col]   if desc_col   else [""] * n
        cats    = batch[cat_col]    if cat_col    else [""] * n
        genders = batch[gender_col] if gender_col else [""] * n

        if has_images:
            pil_images = batch["image"]
            embs = embed_images_batch(pil_images)
        else:
            # Text-only dataset — embed the description
            embs = [embed_text(str(d)) for d in descs]

        all_embeddings.extend(embs)

        for i in range(n):
            img_path = images_dir / f"{start + i}.jpg"

            if has_images:
                batch["image"][i].convert("RGB").save(img_path, quality=85)
                img_url = f"/catalog/images/{start + i}.jpg"
            elif img_url_col and batch[img_url_col][i]:
                img_url = batch[img_url_col][i]  # external URL
            else:
                img_url = ""

            cat_raw = str(cats[i]) if cats[i] else ""
            norm_cat = _normalize_category(cat_raw, "", "")

            desc = str(descs[i])[:200] if descs[i] else ""

            meta.append({
                "id": str(start + i),
                "description": desc,
                "category": norm_cat or "Top",
                "article_type": cat_raw,
                "gender": str(genders[i]) if genders[i] else "",
                "image_url": img_url,
            })

        if start % (batch_size * 10) == 0:
            log.info("Indexed %d/%d items", end, total)

    embeddings_np = np.array(all_embeddings, dtype="float32")
    faiss.normalize_L2(embeddings_np)
    dim = embeddings_np.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings_np)

    faiss.write_index(index, str(_INDEX_FILE))
    with open(_META_FILE, "w") as f:
        json.dump(meta, f)

    _index = index
    _meta = meta
    log.info("Catalog index built: %d items", len(meta))


def _normalize_category(article: str, sub: str, master: str) -> str | None:
    combined = (article + " " + sub + " " + master).lower()

    if any(w in combined for w in ["shoe", "sneaker", "boot", "heel", "sandal", "loafer", "footwear", "flip flop", "moccasin"]):
        return "Shoes"

    if any(w in combined for w in ["jacket", "coat", "blazer", "windcheater", "overcoat", "parka", "outerwear"]):
        return "Outerwear"

    if any(w in combined for w in ["trouser", "jean", "skirt", "short", "pant", "legging", "capri", "jogger", "bottomwear"]):
        return "Bottom"

    if any(w in combined for w in ["shirt", "t-shirt", "tshirt", "top", "blouse", "sweater", "sweatshirt", "hoodie", "polo", "vest", "tunic", "dress", "jumpsuit", "topwear"]):
        return "Top"

    return None


async def search_outfit(profile: dict) -> dict:
    await _ensure_loaded()
    return await asyncio.to_thread(_search_outfit_sync, profile)


async def swap_item(profile: dict, category: str, exclude_id: str | None = None) -> dict | None:
    await _ensure_loaded()
    return await asyncio.to_thread(_search_category_sync, profile, category, exclude_id)


def _build_query(profile: dict) -> str:
    gender = profile.get("gender", "")
    style  = profile.get("style_pref") or "casual"
    build  = profile.get("build", "")
    colour = profile.get("coloring", "")
    return f"{gender} {style} {colour} {build} fashion clothing apparel".strip()


def _search_outfit_sync(profile: dict) -> dict:
    import faiss
    from services.fashionclip import embed_text

    gender_filter = profile.get("gender", "unisex").lower()

    query = _build_query(profile)
    q_vec = embed_text(query).reshape(1, -1).astype("float32")
    faiss.normalize_L2(q_vec)

    k = min(500, len(_meta))
    D, I = _index.search(q_vec, k)

    outfit = {}
    for idx in I[0]:
        if idx < 0:
            continue
        item = _meta[idx]
        cat = item["category"]
        if cat in outfit:
            continue
        if not _gender_match(item.get("gender", ""), gender_filter):
            continue
        outfit[cat] = {**item}
        if len(outfit) >= 4:
            break

    return outfit


def _search_category_sync(profile: dict, category: str, exclude_id: str | None) -> dict | None:
    import faiss
    from services.fashionclip import embed_text

    gender_filter = profile.get("gender", "unisex").lower()
    style = profile.get("style_pref", "casual")
    query = f"{gender_filter} {style} {category.lower()}"
    q_vec = embed_text(query).reshape(1, -1).astype("float32")
    faiss.normalize_L2(q_vec)

    k = min(300, len(_meta))
    D, I = _index.search(q_vec, k)

    for idx in I[0]:
        if idx < 0:
            continue
        item = _meta[idx]
        if item["category"] != category or item["id"] == exclude_id:
            continue
        if not _gender_match(item.get("gender", ""), gender_filter):
            continue
        return {**item}

    return None


def _gender_match(item_gender: str, requested: str) -> bool:
    if requested in ("unisex", ""):
        return True
    ig = item_gender.lower()
    if ig in ("unisex", ""):
        return True
    if requested == "men" and ig in ("men", "boys"):
        return True
    if requested == "women" and ig in ("women", "girls"):
        return True
    return False


def get_item_image_path(item_id: str) -> Path | None:
    path = CATALOG_DIR / "images" / f"{item_id}.jpg"
    return path if path.exists() else None
