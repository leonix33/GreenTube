from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.catalog.ingestion import CatalogIngestionService
from app.catalog.service import CatalogService
from app.config import get_settings
from app.database.client import get_catalog_db, is_mongodb_connected
from app.database.repositories.tracks import TrackRepository
from app.integrations.youtube_client import configured as youtube_configured
from app.integrations.youtube_client import search_music_video_id
from app.providers.audius import AudiusCatalogProvider
from app.providers.deezer import DeezerCatalogProvider
from app.providers.jamendo import JamendoCatalogProvider
from app.providers.local import LocalCatalogProvider
from app.providers.musicbrainz import MusicBrainzCatalogProvider

router = APIRouter(prefix="/admin/catalog", tags=["admin-catalog"])
settings = get_settings()


async def require_admin_key(x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key")):
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin import API is not configured (set ADMIN_API_KEY)",
        )
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin key")


def _require_mongo() -> CatalogIngestionService:
    db = get_catalog_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MongoDB catalog unavailable",
        )
    return CatalogIngestionService(db)


@router.get("/stats")
async def catalog_stats(_: None = Depends(require_admin_key)):
    service = CatalogService()
    stats = await service.stats()
    stats["mongodb_connected"] = is_mongodb_connected()
    stats["providers"] = {
        "local": True,
        "jamendo": bool(settings.jamendo_client_id),
        "audius": True,
        "deezer": True,
        "musicbrainz": True,
    }
    return stats


@router.post("/import/local")
async def import_local(
    limit: int = Query(default=10_000, le=10_000),
    _: None = Depends(require_admin_key),
    ingestion: CatalogIngestionService = Depends(_require_mongo),
):
    return await ingestion.ingest(LocalCatalogProvider(), limit=limit)


@router.post("/import/jamendo")
async def import_jamendo(
    genre: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = Query(default=100, le=200),
    _: None = Depends(require_admin_key),
    ingestion: CatalogIngestionService = Depends(_require_mongo),
):
    provider = JamendoCatalogProvider()
    if not provider.configured:
        raise HTTPException(status_code=503, detail="JAMENDO_CLIENT_ID not configured")
    return await ingestion.ingest(provider, query=query, genre=genre, limit=limit)


@router.post("/import/audius")
async def import_audius(
    genre: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = Query(default=100, le=100),
    _: None = Depends(require_admin_key),
    ingestion: CatalogIngestionService = Depends(_require_mongo),
):
    provider = AudiusCatalogProvider()
    return await ingestion.ingest(provider, query=query, genre=genre, limit=limit)


@router.post("/import/deezer")
async def import_deezer(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=25, le=50),
    _: None = Depends(require_admin_key),
    ingestion: CatalogIngestionService = Depends(_require_mongo),
):
    """Import Deezer search hits as 30-second preview streams (official API)."""
    provider = DeezerCatalogProvider()
    return await ingestion.ingest(provider, query=query, limit=limit)


@router.post("/import/musicbrainz")
async def import_musicbrainz(
    genre: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    _: None = Depends(require_admin_key),
    ingestion: CatalogIngestionService = Depends(_require_mongo),
):
    provider = MusicBrainzCatalogProvider()
    return await ingestion.ingest(provider, query=query or "recording:*", genre=genre, limit=limit)


class MusicVideoAttach(BaseModel):
    youtube_video_id: Optional[str] = Field(default=None, min_length=6, max_length=20)
    video_url: Optional[str] = Field(default=None, min_length=8)


@router.put("/tracks/{track_id}/music-video")
async def attach_music_video(
    track_id: str,
    body: MusicVideoAttach,
    _: None = Depends(require_admin_key),
):
    if not body.youtube_video_id and not body.video_url:
        raise HTTPException(status_code=400, detail="Provide youtube_video_id or video_url")
    db = get_catalog_db()
    if db is None:
        raise HTTPException(status_code=503, detail="MongoDB unavailable")
    repo = TrackRepository(db)
    doc = await repo.get_by_id(track_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Track not found")
    mv: dict = {}
    if body.youtube_video_id:
        mv = {"kind": "youtube", "youtube_video_id": body.youtube_video_id.strip()}
    else:
        mv = {"kind": "stream", "video_url": body.video_url.strip()}
    await db.tracks.update_one(
        {"_id": doc["_id"]},
        {"$set": {"playback.music_video": mv, "updated_at": datetime.now(timezone.utc)}},
    )
    return {"track_id": track_id, "music_video": mv}


@router.post("/music-videos/match-youtube")
async def match_youtube_music_videos(
    limit: int = Query(default=25, ge=1, le=100),
    _: None = Depends(require_admin_key),
):
    if not youtube_configured():
        raise HTTPException(status_code=503, detail="Set YOUTUBE_API_KEY in API .env")
    db = get_catalog_db()
    if db is None:
        raise HTTPException(status_code=503, detail="MongoDB unavailable")
    matched = 0
    cursor = (
        db.tracks.find({"playback.available": True})
        .sort("discovery.trending_score", -1)
        .limit(limit * 3)
    )
    checked = 0
    async for doc in cursor:
        if checked >= limit:
            break
        playback = doc.get("playback") or {}
        if (playback.get("music_video") or {}).get("youtube_video_id"):
            continue
        artist = (doc.get("artist") or {}).get("name") or ""
        title = doc.get("title") or ""
        if not artist or not title:
            continue
        checked += 1
        vid = await search_music_video_id(title=title, artist=artist)
        if not vid:
            continue
        await db.tracks.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "playback.music_video": {"kind": "youtube", "youtube_video_id": vid},
                }
            },
        )
        matched += 1
    return {"checked": checked, "matched": matched, "youtube_api": True}
