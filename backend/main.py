import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from services import logbuffer
from routes import analyze, outfit, tryon

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
app.include_router(tryon.router, prefix="/api")

OUTFITS_DIR = Path(os.environ.get("OUTFITS_DIR", "./outfits"))
FRONTEND_DIST = Path(os.environ.get("FRONTEND_DIST", ""))
OUTFITS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/files", StaticFiles(directory=str(OUTFITS_DIR)), name="files")


@app.get("/api/logs")
def get_logs():
    return logbuffer.get_logs()


if FRONTEND_DIST and FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="spa")
