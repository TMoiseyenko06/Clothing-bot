import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from services import logbuffer
from routes import analyze, outfit, history

logbuffer.setup()

app = FastAPI(title="AI Outfit Builder")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api")
app.include_router(outfit.router, prefix="/api")
app.include_router(history.router, prefix="/api")

OUTFITS_DIR = Path(os.environ.get("OUTFITS_DIR", "./outfits"))
OUTFITS_DIR.mkdir(parents=True, exist_ok=True)

# Serve selfie photos and cached product images
app.mount("/files", StaticFiles(directory=str(OUTFITS_DIR)), name="files")
