from pydantic import BaseModel
from typing import Optional, List


class OnboardingAnswers(BaseModel):
    gender: str
    fit: str
    budget: str
    occasion: str


class Feedback(BaseModel):
    rating: int
    text: str


class OutfitPiece(BaseModel):
    category: str
    name: str
    brand: str
    price: str
    link: str
    image_url: str
    why: str
    cached_image: Optional[str] = None


class Outfit(BaseModel):
    outfit_concept: str
    pieces: List[OutfitPiece]


class Session(BaseModel):
    session_id: str
    selfie_path: str
    style_profile: str
    onboarding: Optional[OnboardingAnswers] = None
    outfits: List[dict] = []
    feedbacks: List[dict] = []
    created_at: str
    updated_at: str
