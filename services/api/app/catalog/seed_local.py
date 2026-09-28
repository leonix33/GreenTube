from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.catalog.ingestion import CatalogIngestionService
from app.providers.local import LocalCatalogProvider


async def seed_local_catalog(db: AsyncIOMotorDatabase) -> dict:
    """Migrate existing demo WAV catalog into MongoDB (idempotent)."""
    service = CatalogIngestionService(db)
    return await service.ingest(LocalCatalogProvider(), limit=10_000)
