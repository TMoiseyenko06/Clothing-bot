import asyncio
import io
import logging
import numpy as np

log = logging.getLogger(__name__)

_seg_model = None
_seg_processor = None
_pipe = None
_tryon_lock = asyncio.Lock()

# SegFormer label indices for mattmdjaga/segformer_b2_clothes
_SEG_UPPER = [5, 6, 7]       # upper-clothes, dress, coat
_SEG_LOWER = [9, 12]         # pants, skirt
_SEG_SHOES = [18, 19]        # left-shoe, right-shoe
_SEG_FULL = [5, 6, 7, 9, 12] # full body (dress)

_CATEGORY_MASK = {
    "Top": _SEG_UPPER,
    "Bottom": _SEG_LOWER,
    "Shoes": _SEG_SHOES,
    "Outerwear": _SEG_UPPER,
    "Dress": _SEG_FULL,
}


async def _ensure_loaded():
    global _seg_model, _seg_processor, _pipe
    if _pipe is not None:
        return
    async with _tryon_lock:
        if _pipe is not None:
            return
        await asyncio.to_thread(_load_models)


def _load_models():
    global _seg_model, _seg_processor, _pipe
    import torch
    from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
    from diffusers import StableDiffusionInpaintPipeline

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    log.info("Loading SegFormer clothes segmentation...")
    _seg_processor = SegformerImageProcessor.from_pretrained("mattmdjaga/segformer_b2_clothes")
    _seg_model = SegformerForSemanticSegmentation.from_pretrained(
        "mattmdjaga/segformer_b2_clothes"
    ).to(device)
    _seg_model.eval()

    log.info("Loading SD 1.5 inpainting + IP-Adapter on %s...", device)
    _pipe = StableDiffusionInpaintPipeline.from_pretrained(
        "runwayml/stable-diffusion-inpainting",
        torch_dtype=dtype,
        safety_checker=None,
        requires_safety_checker=False,
    )
    _pipe.load_ip_adapter("h94/IP-Adapter", subfolder="models", weight_name="ip-adapter_sd15.bin")
    _pipe.set_ip_adapter_scale(0.9)
    _pipe.enable_attention_slicing()
    _pipe = _pipe.to(device)
    log.info("Try-on pipeline ready on %s", device)


def _generate_mask(person_img, label_indices: list[int]):
    import torch
    from PIL import Image, ImageFilter

    device = next(_seg_model.parameters()).device
    inputs = _seg_processor(images=person_img, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        logits = _seg_model(**inputs).logits

    seg_map = logits.argmax(dim=1)[0].cpu().numpy().astype(np.uint8)
    seg_pil = Image.fromarray(seg_map).resize(person_img.size, Image.NEAREST)
    seg_arr = np.array(seg_pil)

    mask = np.zeros_like(seg_arr, dtype=np.uint8)
    for label in label_indices:
        mask[seg_arr == label] = 255

    return Image.fromarray(mask).filter(ImageFilter.MaxFilter(size=21))


def _run_tryon(person_bytes: bytes, garment_bytes: bytes, category: str) -> bytes:
    from PIL import Image

    person_img = Image.open(io.BytesIO(person_bytes)).convert("RGB").resize((512, 512))
    garment_img = Image.open(io.BytesIO(garment_bytes)).convert("RGB").resize((512, 512))

    label_indices = _CATEGORY_MASK.get(category, _SEG_UPPER)
    mask = _generate_mask(person_img, label_indices)

    result = _pipe(
        prompt=f"person wearing {category.lower()}, fashion photography, high quality, realistic",
        negative_prompt="bad quality, distorted, blurry, deformed, artifacts",
        image=person_img,
        mask_image=mask,
        ip_adapter_image=garment_img,
        num_inference_steps=30,
        guidance_scale=7.5,
        strength=0.99,
    ).images[0]

    buf = io.BytesIO()
    result.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


async def generate(person_bytes: bytes, garment_bytes: bytes, category: str) -> bytes:
    await _ensure_loaded()
    async with _tryon_lock:
        return await asyncio.to_thread(_run_tryon, person_bytes, garment_bytes, category)
