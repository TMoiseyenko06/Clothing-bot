import asyncio
import io
import logging
import os
import uuid
from pathlib import Path

import httpx
import numpy as np
import torch
from PIL import Image, ImageFilter

log = logging.getLogger(__name__)

OUTFITS_DIR = Path(os.environ.get("OUTFITS_DIR", "./outfits"))

# SegFormer mattmdjaga/segformer_b2_clothes label ids
_CATEGORY_LABELS = {
    "Top":       [4],        # Upper-clothes
    "Bottom":    [5, 6],     # Skirt, Pants
    "Shoes":     [9, 10],    # Left-shoe, Right-shoe
    "Outerwear": [4],        # Upper-clothes (jacket covers same region)
    "Accessory": [16, 17],   # Bag, Scarf
}

_seg_processor = None
_seg_model = None
_inpaint_pipe = None


def _load_seg():
    global _seg_processor, _seg_model
    if _seg_model is not None:
        return
    from transformers import SegformerImageProcessor, AutoModelForSemanticSegmentation
    log.info("Loading segmentation model (mattmdjaga/segformer_b2_clothes)…")
    _seg_processor = SegformerImageProcessor.from_pretrained("mattmdjaga/segformer_b2_clothes")
    _seg_model = AutoModelForSemanticSegmentation.from_pretrained("mattmdjaga/segformer_b2_clothes")
    _seg_model.eval()
    log.info("Segmentation model ready")


def _load_inpaint():
    global _inpaint_pipe
    if _inpaint_pipe is not None:
        return
    from diffusers import StableDiffusionInpaintPipeline
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    log.info("Loading SD-1.5 inpainting + IP-Adapter on %s…", device)
    pipe = StableDiffusionInpaintPipeline.from_pretrained(
        "runwayml/stable-diffusion-inpainting",
        torch_dtype=dtype,
        safety_checker=None,
        requires_safety_checker=False,
    ).to(device)
    pipe.load_ip_adapter("h94/IP-Adapter", subfolder="models", weight_name="ip-adapter_sd15.bin")
    pipe.set_ip_adapter_scale(0.75)
    pipe.enable_attention_slicing()
    _inpaint_pipe = pipe
    log.info("Inpainting pipeline ready")


async def _fetch_image(url: str) -> Image.Image:
    # Local /files/ URLs served by FastAPI
    if url.startswith("/files/"):
        rel = url[len("/files/"):]
        path = OUTFITS_DIR / rel
        return Image.open(path).convert("RGB")
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def _build_mask(person: Image.Image, category: str) -> Image.Image:
    label_ids = _CATEGORY_LABELS.get(category, [4])
    inputs = _seg_processor(images=person, return_tensors="pt")
    with torch.no_grad():
        logits = _seg_model(**inputs).logits  # (1, C, H, W)
    pred = logits.argmax(dim=1).squeeze(0).numpy().astype(np.uint8)  # (H, W)

    mask_arr = np.zeros_like(pred)
    for lbl in label_ids:
        mask_arr[pred == lbl] = 255

    if mask_arr.max() == 0:
        # Fallback: draw a generous rectangle over expected clothing area
        h, w = mask_arr.shape
        if category in ("Top", "Outerwear"):
            mask_arr[h // 5: 3 * h // 5, w // 6: 5 * w // 6] = 255
        elif category == "Bottom":
            mask_arr[h // 2: 9 * h // 10, w // 6: 5 * w // 6] = 255
        elif category == "Shoes":
            mask_arr[8 * h // 10:, w // 6: 5 * w // 6] = 255
        else:
            mask_arr[h // 5: 4 * h // 5, w // 6: 5 * w // 6] = 255

    mask = Image.fromarray(mask_arr).resize(person.size, Image.NEAREST)
    mask = mask.filter(ImageFilter.MaxFilter(size=21))   # dilate edges
    return mask


def _run_sync(person: Image.Image, garment: Image.Image, category: str, mask: Image.Image) -> Image.Image:
    work_size = (512, 768)
    person_r = person.resize(work_size, Image.LANCZOS)
    mask_r = mask.resize(work_size, Image.NEAREST)
    garment_r = garment.resize((512, 512), Image.LANCZOS)

    prompt = (
        f"fashion photo of a person wearing {category.lower()}, "
        "studio lighting, full body, high quality, photorealistic"
    )
    negative = (
        "deformed, ugly, bad anatomy, cartoon, painting, sketch, "
        "watermark, text, multiple people, blurry"
    )

    result = _inpaint_pipe(
        prompt=prompt,
        negative_prompt=negative,
        image=person_r,
        mask_image=mask_r,
        ip_adapter_image=garment_r,
        num_inference_steps=30,
        guidance_scale=7.5,
        strength=0.99,
    ).images[0]

    # Soft-composite result onto person (keep face/background intact)
    mask_soft = mask_r.filter(ImageFilter.GaussianBlur(6)).convert("L")
    composite = Image.composite(result, person_r, mask_soft)
    return composite


async def run_tryon(session_id: str, selfie_path: str, garment_url: str, category: str) -> str:
    await asyncio.to_thread(_load_seg)
    await asyncio.to_thread(_load_inpaint)

    person = Image.open(selfie_path).convert("RGB")
    garment = await _fetch_image(garment_url)

    mask = await asyncio.to_thread(_build_mask, person, category)
    result = await asyncio.to_thread(_run_sync, person, garment, category, mask)

    out_dir = OUTFITS_DIR / session_id
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"tryon_{uuid.uuid4().hex[:8]}.jpg"
    out_path = out_dir / fname
    result.save(out_path, quality=90)

    log.info("Try-on saved: %s", out_path)
    return str(out_path)
