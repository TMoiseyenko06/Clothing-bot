import asyncio
import io
import logging
import os

log = logging.getLogger(__name__)

HF_MODEL = os.environ.get("HF_MODEL", "")

_model = None
_processor = None
_load_lock = asyncio.Lock()

_STYLE_LABELS = [
    "casual everyday style", "formal office style", "streetwear urban style",
    "preppy classic style", "bohemian free-spirited style", "minimalist clean style",
    "sporty athletic style", "vintage retro style", "smart casual style",
]
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


async def _load():
    global _model, _processor
    if _model is not None:
        return
    async with _load_lock:
        if _model is not None:
            return
        log.info("Loading FashionCLIP model '%s' — first run may take a moment", HF_MODEL)
        import torch
        from transformers import CLIPModel, CLIPProcessor
        _model = CLIPModel.from_pretrained(HF_MODEL)
        _processor = CLIPProcessor.from_pretrained(HF_MODEL)
        _model.eval()
        log.info("FashionCLIP loaded successfully")


def _top_label(image, labels: list[str]) -> str:
    import torch
    inputs = _processor(text=labels, images=image, return_tensors="pt", padding=True)
    with torch.no_grad():
        logits = _model(**inputs).logits_per_image
    return labels[int(logits.softmax(dim=1)[0].argmax())]


def _run_analysis(image_bytes: bytes) -> str:
    from PIL import Image
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    style    = _top_label(image, _STYLE_LABELS)
    coloring = _top_label(image, _COLORING_LABELS)
    undertone = _top_label(image, _UNDERTONE_LABELS)
    build    = _top_label(image, _BUILD_LABELS)
    hair     = _top_label(image, _HAIR_LABELS)

    log.info("FashionCLIP — style=%s coloring=%s undertone=%s build=%s hair=%s",
             style, coloring, undertone, build, hair)

    return (
        f"Style profile (analyzed locally with FashionCLIP — {HF_MODEL}):\n"
        f"• Skin tone: {coloring} with {undertone}\n"
        f"• Body type: {build}\n"
        f"• Hair: {hair}\n"
        f"• Current style aesthetic: {style}\n\n"
        "Use these specific attributes to recommend a cohesive outfit that "
        "flatters and complements this person."
    )


async def analyze_selfie_local(image_bytes: bytes) -> str:
    await _load()
    return await asyncio.to_thread(_run_analysis, image_bytes)
