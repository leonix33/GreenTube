"""Import playable afrobeats tracks into MongoDB (Audius + optional Jamendo)."""

from __future__ import annotations

import asyncio

from app.catalog.ingestion import CatalogIngestionService
from app.catalog.service import CatalogService
from app.config import get_settings
from app.database.client import close_mongodb, connect_mongodb, get_catalog_db
from app.database.indexes import ensure_catalog_indexes
from app.providers.audius import AudiusCatalogProvider
from app.providers.jamendo import JamendoCatalogProvider

TARGET = 1000
GENRE = "afrobeats"
AUDIUS_QUERIES = [
    "afrobeats",
    "afrobeat",
    "afropop",
    "amapiano",
    "afroswing",
    "afro house",
    "nigeria",
    "lagos",
    "burna",
    "wizkid",
    "davido",
    "african",
    "dancehall",
    "ghana",
    "afro fusion",
    "afro r&b",
    "alté",
    "asake",
    "rema",
    "tems",
]


async def main() -> None:
    settings = get_settings()
    if not await connect_mongodb(settings.mongodb_uri, settings.mongodb_database):
        raise SystemExit("MongoDB unavailable")

    db = get_catalog_db()
    assert db is not None
    await ensure_catalog_indexes(db)
    ingestion = CatalogIngestionService(db)

    summary: list[dict] = []
    playable_before = await db.tracks.count_documents({"playback.available": True, "genres": GENRE})

    audius = AudiusCatalogProvider()
    per_query = 250
    for q in AUDIUS_QUERIES:
        remaining = TARGET - await db.tracks.count_documents(
            {"genres": GENRE, "playback.available": True}
        )
        if remaining <= 0:
            break
        result = await ingestion.ingest(
            audius,
            query=q,
            genre=GENRE,
            limit=min(per_query, remaining + 50),
        )
        summary.append({"provider": "audius", "query": q, **result})

    jamendo = JamendoCatalogProvider()
    if jamendo.configured:
        remaining = TARGET - await db.tracks.count_documents(
            {"genres": GENRE, "playback.available": True}
        )
        if remaining > 0:
            result = await ingestion.ingest(
                jamendo,
                genre=GENRE,
                query="afro",
                limit=min(remaining, 1000),
            )
            summary.append({"provider": "jamendo", "query": "afro", **result})
    else:
        summary.append({"provider": "jamendo", "skipped": True, "reason": "JAMENDO_CLIENT_ID not set"})

    stats = await CatalogService().stats()
    afrobeats_playable = await db.tracks.count_documents({"genres": GENRE, "playback.available": True})
    print(
        {
            "target": TARGET,
            "afrobeats_playable_before": playable_before,
            "afrobeats_playable_after": afrobeats_playable,
            "imports": summary,
            "catalog_stats": stats,
        }
    )
    await close_mongodb()


if __name__ == "__main__":
    asyncio.run(main())
