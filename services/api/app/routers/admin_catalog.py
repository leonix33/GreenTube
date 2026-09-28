from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.catalog.ingestion import CatalogIngestionService
from app.catalog.service import CatalogService
from app.config import get_settings
from app.database.client import get_catalog_db, is_mongodb_connected
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
