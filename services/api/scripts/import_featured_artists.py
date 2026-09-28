"""Import and tag tracks for curated major artists (Audius search + quality filters)."""

from __future__ import annotations

import asyncio
import json
import sys

from app.catalog.featured_artists import (
    FEATURED_ARTISTS,
    apply_featured_discovery,
    match_featured_artist,
)
from app.catalog.ingestion import CatalogIngestionService
from app.catalog.service import CatalogService
from app.config import get_settings
from app.database.client import close_mongodb, connect_mongodb, get_catalog_db
from app.database.indexes import ensure_catalog_indexes
from app.providers.audius import AudiusCatalogProvider

PER_ARTIST = int(__import__("os").environ.get("IMPORT_PER_ARTIST", "80"))


async def backfill_tags(db) -> int:
    """Tag existing catalog rows that match star names."""
    updated = 0
    async for doc in db.tracks.find({"playback.available": True}):
        title = doc.get("title") or ""
        artist = (doc.get("artist") or {}).get("name") or ""
        star = match_featured_artist(title, artist)
        if not star:
            continue
        plays = float((doc.get("stats") or {}).get("plays") or 0)
        genres = list(doc.get("genres") or [])
        for g in star.genres:
            if g not in genres:
                genres.append(g)
        await db.tracks.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "discovery.featured_artist": star.slug,
                    "discovery.featured_artist_name": star.name,
                    "discovery.trending_score": 10_000_000 + plays,
                    "genres": genres,
                },
            },
        )
        updated += 1
    return updated


async def main() -> None:
    settings = get_settings()
    if not await connect_mongodb(settings.mongodb_uri, settings.mongodb_database):
        raise SystemExit("MongoDB unavailable")

    db = get_catalog_db()
    assert db is not None
    await ensure_catalog_indexes(db)
    ingestion = CatalogIngestionService(db)
    audius = AudiusCatalogProvider()

    summary: list[dict] = []
    for star in FEATURED_ARTISTS:
        raw = await audius.import_tracks(query=star.name, limit=PER_ARTIST * 3)
        filtered: list[dict] = []
        for track in raw:
            title = track.get("title") or ""
            artist = (track.get("artist") or {}).get("name") or ""
            matched = match_featured_artist(title, artist)
            if matched is None or matched.slug != star.slug:
                continue
            apply_featured_discovery(track, star)
            filtered.append(track)
            if len(filtered) >= PER_ARTIST:
                break

        imported = updated = failed = 0
        for track in filtered:
            try:
                from app.catalog.dedupe import find_existing_track
                from app.database.repositories.artists import ArtistRepository
                from app.database.repositories.tracks import TrackRepository

                tracks_repo = TrackRepository(db)
                artists_repo = ArtistRepository(db)
                existing = await find_existing_track(db, track)
                artist_doc = await artists_repo.upsert_by_name(
                    star.name,
                    genres=list(star.genres),
                )
                track["artist"] = {"id": artist_doc["_id"], "name": star.name}
                if existing and track.get("_id") is None:
                    track["_id"] = existing["_id"]
                _, created = await tracks_repo.upsert_track(track)
                if created:
                    imported += 1
                else:
                    updated += 1
            except Exception:
                failed += 1

        summary.append(
            {
                "artist": star.slug,
                "name": star.name,
                "candidates": len(raw),
                "matched": len(filtered),
                "imported": imported,
                "updated": updated,
                "failed": failed,
            }
        )
        print(f"[featured] {star.name}: {len(filtered)} tracks", file=sys.stderr, flush=True)

    tagged = await backfill_tags(db)
    stats = await CatalogService().stats()
    featured_count = await db.tracks.count_documents(
        {"playback.available": True, "discovery.featured_artist": {"$exists": True}}
    )
    print(
        json.dumps(
            {
                "per_artist_target": PER_ARTIST,
                "featured_playable": featured_count,
                "backfill_tagged": tagged,
                "artists": summary,
                "catalog_stats": stats,
            },
            indent=2,
        )
    )
    await close_mongodb()


if __name__ == "__main__":
    asyncio.run(main())
