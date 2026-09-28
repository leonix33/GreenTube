"""Bulk-import playable tracks for every browse genre (Audius + optional Jamendo)."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Iterable

from app.catalog.ingestion import CatalogIngestionService
from app.catalog.service import CatalogService
from app.catalog_seed import GENRES, GenreInfo
from app.config import get_settings
from app.database.client import close_mongodb, connect_mongodb, get_catalog_db
from app.database.indexes import ensure_catalog_indexes
from app.database.repositories.genres import GenreRepository
from app.providers.audius import AudiusCatalogProvider
from app.providers.jamendo import JamendoCatalogProvider

# Playable tracks to aim for per browse slug (skips genres already at/above target).
PER_GENRE_TARGET = int(os.environ.get("IMPORT_PER_GENRE", "400"))

# Extra Audius text searches when the genre name alone is thin.
EXTRA_AUDIUS_QUERIES: dict[str, list[str]] = {
    "afrobeats": ["afropop", "amapiano"],
    "hip-hop": ["rap", "trap", "drill", "boom bap", "hip hop beats"],
    "rnb": ["r&b", "neo soul"],
    "electronic": ["edm", "bass music"],
    "house": ["deep house", "tech house"],
    "techno": ["minimal techno"],
    "k-pop": ["kpop", "korean pop"],
    "latin": ["reggaeton", "latin pop"],
    "metal": ["heavy metal", "metalcore"],
    "classical": ["orchestra", "piano classical"],
    "ambient": ["drone ambient"],
    "chill": ["lofi", "chillhop"],
    "focus": ["study beats", "lofi focus"],
    "workout": ["gym", "fitness"],
    "late-night": ["night drive", "slow jam"],
    "soundtrack": ["cinematic", "film score"],
    "world": ["world music", "afro"],
    "gospel": ["worship", "christian"],
    "country": ["country pop"],
    "folk": ["acoustic folk"],
    "indie": ["indie rock"],
    "pop": ["indie pop"],
    "rock": ["alternative rock"],
    "punk": ["pop punk"],
    "reggae": ["roots reggae"],
    "dancehall": ["dancehall reggae", "bashment", "dancehall riddim"],
    "jazz": ["smooth jazz"],
    "blues": ["electric blues", "delta blues", "blues rock", "blues guitar"],
    "soul": ["motown", "neo soul", "soul music", "slow soul"],
    "funk": ["disco funk"],
    "instrumental": ["instrumental beats"],
}


def _dedupe_strings(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        q = raw.strip()
        if not q:
            continue
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(q)
    return out


def audius_queries_for(genre: GenreInfo) -> list[str]:
    base = [
        genre.name,
        genre.slug.replace("-", " "),
    ]
    base.extend(EXTRA_AUDIUS_QUERIES.get(genre.slug, []))
    return _dedupe_strings(base)


async def main() -> None:
    settings = get_settings()
    if not await connect_mongodb(settings.mongodb_uri, settings.mongodb_database):
        raise SystemExit("MongoDB unavailable")

    db = get_catalog_db()
    assert db is not None
    await ensure_catalog_indexes(db)
    ingestion = CatalogIngestionService(db)
    genres_repo = GenreRepository(db)

    audius = AudiusCatalogProvider()
    jamendo = JamendoCatalogProvider()

    playable_before = await db.tracks.count_documents({"playback.available": True})
    per_genre_summary: list[dict] = []

    for genre in GENRES:
        slug = genre.slug
        current = await db.tracks.count_documents(
            {"genres": slug, "playback.available": True}
        )
        need = PER_GENRE_TARGET - current
        if need <= 0:
            per_genre_summary.append(
                {"genre": slug, "skipped": True, "playable_with_genre": current}
            )
            continue

        genre_runs: list[dict] = []
        for query in audius_queries_for(genre):
            remaining = PER_GENRE_TARGET - await db.tracks.count_documents(
                {"genres": slug, "playback.available": True}
            )
            if remaining <= 0:
                break
            batch = min(250, remaining + 30)
            result = await ingestion.ingest(
                audius,
                query=query,
                genre=slug,
                limit=batch,
            )
            genre_runs.append({"query": query, **result})

        if jamendo.configured:
            remaining = PER_GENRE_TARGET - await db.tracks.count_documents(
                {"genres": slug, "playback.available": True}
            )
            if remaining > 0:
                result = await ingestion.ingest(
                    jamendo,
                    genre=slug,
                    query=genre.name.split()[0].lower(),
                    limit=min(200, remaining + 20),
                )
                genre_runs.append({"provider": "jamendo", **result})

        after = await db.tracks.count_documents(
            {"genres": slug, "playback.available": True}
        )
        per_genre_summary.append(
            {
                "genre": slug,
                "playable_before": current,
                "playable_after": after,
                "target": PER_GENRE_TARGET,
                "runs": genre_runs,
            }
        )
        print(f"[import] {slug}: {current} -> {after}", file=sys.stderr, flush=True)

    await genres_repo.sync_taxonomy_from_seed()
    await genres_repo.refresh_track_counts()

    stats = await CatalogService().stats()
    playable_after = await db.tracks.count_documents({"playback.available": True})

    report = {
        "per_genre_target": PER_GENRE_TARGET,
        "playable_total_before": playable_before,
        "playable_total_after": playable_after,
        "genres": len(GENRES),
        "catalog_stats": stats,
        "by_genre": per_genre_summary,
    }
    print(json.dumps(report, indent=2))
    await close_mongodb()


if __name__ == "__main__":
    asyncio.run(main())
