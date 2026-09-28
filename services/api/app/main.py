from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.catalog.seed_local import seed_local_catalog
from app.catalog_seed import ensure_demo_audio
from app.config import get_settings
from app.database.client import close_mongodb, connect_mongodb, get_catalog_db, mongodb_health
from app.database.indexes import ensure_catalog_indexes
from app.routers import admin_catalog, auth, catalog, playback, spotify_integration

settings = get_settings()
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_demo_audio()
    connected = await connect_mongodb(settings.mongodb_uri, settings.mongodb_database)
    if connected:
        db = get_catalog_db()
        if db is not None:
            await ensure_catalog_indexes(db)
            if settings.auto_seed_mongo:
                await seed_local_catalog(db)
    yield
    await close_mongodb()


app = FastAPI(
    title="GreenTube Music API",
    version="0.1.0",
    description="Catalog, auth, playlists, and playback for GreenTube Music.",
    lifespan=lifespan,
)

_cors_common = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.environment == "development":
    # Next may bind :3001, :3002, etc. when :3000 is taken.
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        **_cors_common,
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        **_cors_common,
    )

app.include_router(auth.router, prefix="/api")
app.include_router(catalog.router, prefix="/api")
app.include_router(admin_catalog.router, prefix="/api")
app.include_router(playback.router, prefix="/api")
app.include_router(spotify_integration.router, prefix="/api")

STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "audio").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
async def health():
    mongo = mongodb_health()
    return {
        "status": "ok",
        "service": "green-tube-api",
        "env": settings.environment,
        "mongodb": mongo,
        "catalog_source": "mongodb" if mongo.get("connected") else "seed-open-audio",
    }
