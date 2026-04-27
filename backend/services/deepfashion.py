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
            log.info("Loading DeepFashion index from disk...")
            await asyncio.to_thread(_load_from_disk)
        else:
            log.info("Building DeepFashion index — first run may take several minutes...")
            await asyncio.to_thread(_build_index)


def _load_from_disk():
    global _index, _meta
    import faiss
    _index = faiss.read_index(str(_INDEX_FILE))
    with open(_META_FILE) as f:
        _meta = json.load(f)
    log.info("Loaded %d items from DeepFashion index", len(_meta))


def _build_index():
    global _index, _meta
    import faiss
    from datasets import load_dataset
    from services.fashionclip import embed_images_batch

    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    images_dir = CATALOG_DIR / "images"
    images_dir.mkdir(exist_ok=True)

    log.info("Downloading Marqo/deepfashion-multimodal dataset...")
    ds = load_dataset("Marqo/deepfashion-multimodal", split="data")

    total = len(ds)
    if MAX_ITEMS and MAX_ITEMS < total:
        total = MAX_ITEMS
        ds = ds.select(range(total))

    log.info("Indexing %d items...", total)

    meta = []
    all_embeddings = []
    batch_size = 32

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = ds[start:end]

        pil_images = batch["image"]
        item_ids = batch.get("item_id", [str(i) for i in range(start, end)])
        descriptions = batch.get("description", batch.get("text", [""] * len(pil_images)))
        categories = batch.get("category", [""] * len(pil_images))

        embs = embed_images_batch(pil_images)
        all_embeddings.extend(embs)

        for i, (img, item_id, desc, cat) in enumerate(zip(pil_images, item_ids, descriptions, categories)):
            img_path = images_dir / f"{start + i}.jpg"
            img.convert("RGB").save(img_path, quality=85)
            norm_cat = _normalize_category(str(cat))
            meta.append({
                "id": str(start + i),
                "item_id": str(item_id),
                "description": str(desc)[:200] if desc else "",
                "category": norm_cat or "Top",
                "image_url": f"/catalog/images/{start + i}.jpg",
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
    log.info("DeepFashion index built: %d items", len(meta))


def _normalize_category(raw: str) -> str | None:
    raw = raw.lower()
    if any(w in raw for w in ["shoe", "sneaker", "boot", "heel", "sandal", "loafer"]):
        return "Shoes"
    if any(w in raw for w in ["coat", "outerwear", "cardigan"]):
        return "Outerwear"
    if any(w in raw for w in ["pant", "jean", "skirt", "short", "trouser", "legging"]):
        return "Bottom"
    if any(w in raw for w in ["jacket", "blazer", "shirt", "blouse", "top", "sweater", "tee", "hoodie", "dress", "romper"]):
        return "Top"
    return None


async def search_outfit(profile: dict) -> dict:
    await _ensure_loaded()
    return await asyncio.to_thread(_search_outfit_sync, profile)


async def swap_item(profile: dict, category: str, exclude_id: str | None = None) -> dict | None:
    await _ensure_loaded()
    return await asyncio.to_thread(_search_category_sync, profile, category, exclude_id)


def _build_query(profile: dict) -> str:
    return (
        f"{profile.get('style', 'casual')} clothing for "
        f"{profile.get('build', 'average')} person with "
        f"{profile.get('coloring', 'medium')} complexion"
    )


def _search_outfit_sync(profile: dict) -> dict:
    import faiss
    from services.fashionclip import embed_text

    query = _build_query(profile)
    q_vec = embed_text(query).reshape(1, -1).astype("float32")
    faiss.normalize_L2(q_vec)

    k = min(300, len(_meta))
    D, I = _index.search(q_vec, k)

    outfit = {}
    for idx in I[0]:
        if idx < 0:
            continue
        item = _meta[idx]
        cat = item["category"]
        if cat not in outfit:
            outfit[cat] = {**item}
        if len(outfit) >= 4:
            break

    return outfit


def _search_category_sync(profile: dict, category: str, exclude_id: str | None) -> dict | None:
    import faiss
    from services.fashionclip import embed_text

    query = f"{profile.get('style', 'casual')} {category.lower()}"
    q_vec = embed_text(query).reshape(1, -1).astype("float32")
    faiss.normalize_L2(q_vec)

    k = min(200, len(_meta))
    D, I = _index.search(q_vec, k)

    for idx in I[0]:
        if idx < 0:
            continue
        item = _meta[idx]
        if item["category"] == category and item["id"] != exclude_id:
            return {**item}

    return None


def get_item_image_path(item_id: str) -> Path | None:
    path = CATALOG_DIR / "images" / f"{item_id}.jpg"
    return path if path.exists() else None
