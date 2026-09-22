from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, catalog, playback

settings = get_settings()

app = FastAPI(
    title="GreenTube Music API",
    version="0.1.0",
    description="Catalog, auth, playlists, and playback for GreenTube Music.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(catalog.router, prefix="/api")
app.include_router(playback.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "green-tube-api", "env": settings.environment}
