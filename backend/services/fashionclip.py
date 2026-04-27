import asyncio
import io
import logging
import numpy as np

log = logging.getLogger(__name__)

MODEL_NAME = "patrickjohncyh/fashion-clip"

_model = None
_processor = None
_load_lock = asyncio.Lock()

_COLORING_LABELS = [
    "light fair pale skin tone", "medium light warm skin tone",
    "medium olive skin tone", "medium dark brown skin tone", "dark deep skin tone",
]
_UNDERTONE_LABELS = [
    "warm golden yellow undertones", "cool pink blue undertones", "neutral balanced undertones",
]
_BUILD_LABELS = [
    "slim lean body type", "athletic muscular body type", "average medium body type",
    "tall slender body type", "short petite body type", "fuller curvy body type",
]
_HAIR_LABELS = [
    "blonde light hair", "brown medium hair", "dark black hair",
    "red auburn hair", "grey silver hair",
]


async def _ensure_loaded():
    global _model, _processor
    if _model is not None:
        return
    async with _load_lock:
        if _model is not None:
            return
        log.info("Downloading FashionCLIP weights (~600 MB) — this only happens once...")
        import warnings, torch
        from transformers import CLIPModel, CLIPProcessor
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            _model = CLIPModel.from_pretrained(MODEL_NAME)
            _processor = CLIPProcessor.from_pretrained(MODEL_NAME)
        _model.eval()
        log.info("FashionCLIP loaded")


def _top_label(image, labels: list[str]) -> str:
    import torch
    inputs = _processor(text=labels, images=image, return_tensors="pt", padding=True)
    with torch.no_grad():
        logits = _model(**inputs).logits_per_image
    return labels[int(logits.softmax(dim=1)[0].argmax())]


def _analyze_sync(image_bytes: bytes) -> dict:
    from PIL import Image
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return {
        "coloring": _top_label(image, _COLORING_LABELS),
        "undertone": _top_label(image, _UNDERTONE_LABELS),
        "build": _top_label(image, _BUILD_LABELS),
        "hair": _top_label(image, _HAIR_LABELS),
    }


def embed_text(text: str) -> np.ndarray:
    import torch
    inputs = _processor(text=[text], return_tensors="pt", padding=True)
    with torch.no_grad():
        features = _model.get_text_features(**inputs)
    return features[0].cpu().numpy()


def embed_image(pil_image) -> np.ndarray:
    import torch
    inputs = _processor(images=pil_image, return_tensors="pt")
    with torch.no_grad():
        features = _model.get_image_features(**inputs)
    return features[0].cpu().numpy()


def embed_images_batch(pil_images: list) -> list:
    import torch
    inputs = _processor(images=pil_images, return_tensors="pt", padding=True)
    with torch.no_grad():
        features = _model.get_image_features(**inputs)
    return [f.cpu().numpy() for f in features]


async def analyze_selfie(image_bytes: bytes) -> dict:
    await _ensure_loaded()
    return await asyncio.to_thread(_analyze_sync, image_bytes)
