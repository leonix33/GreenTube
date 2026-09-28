from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.catalog.dedupe import find_existing_track
from app.database.repositories.albums import AlbumRepository
from app.database.repositories.artists import ArtistRepository
from app.database.repositories.genres import GenreRepository
from app.database.repositories.tracks import TrackRepository
from app.providers.base import CatalogProvider


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CatalogIngestionService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db
        self._tracks = TrackRepository(db)
        self._artists = ArtistRepository(db)
        self._albums = AlbumRepository(db)
        self._genres = GenreRepository(db)

    async def ingest(
        self,
        provider: CatalogProvider,
        *,
        query: str | None = None,
        genre: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        started = utcnow()
        requested = limit
        imported = 0
        updated = 0
        duplicates = 0
        failed = 0

        try:
            candidates = await provider.import_tracks(query=query, genre=genre, limit=limit)
        except Exception as exc:  # noqa: BLE001
            await self._db.catalog_imports.insert_one(
                {
                    "provider": provider.name,
                    "query": query,
                    "genre": genre,
                    "requested": requested,
                    "imported": 0,
                    "updated": 0,
                    "duplicates": 0,
                    "failed": requested,
                    "error": str(exc),
                    "started_at": started,
                    "finished_at": utcnow(),
                }
            )
            raise

        for normalized in candidates:
            try:
                existing = await find_existing_track(self._db, normalized)
                artist_doc = await self._artists.upsert_by_name(
                    (normalized.get("artist") or {}).get("name") or "Unknown artist",
                    genres=normalized.get("genres"),
                )
                normalized["artist"] = {
                    "id": artist_doc["_id"],
                    "name": artist_doc["name"],
                }

                album_title = (normalized.get("album") or {}).get("title")
                if album_title:
                    album_doc = await self._albums.upsert_by_title_artist(
                        album_title,
                        artist_doc["_id"],
                        genres=normalized.get("genres"),
                        artwork_url=normalized.get("artwork_url"),
                        release_date=normalized.get("release_date"),
                    )
                    normalized["album"] = {"id": album_doc["_id"], "title": album_doc["title"]}

                if existing and normalized.get("_id") is None:
                    normalized["_id"] = existing["_id"]

                _doc, created = await self._tracks.upsert_track(normalized)
                if existing and not created:
                    duplicates += 1
                    updated += 1
                elif created:
                    imported += 1
                else:
                    updated += 1
            except Exception:
                failed += 1

        await self._genres.sync_taxonomy_from_seed()
        await self._genres.refresh_track_counts()

        result = {
            "provider": provider.name,
            "requested": requested,
            "imported": imported,
            "updated": updated,
            "duplicates": duplicates,
            "failed": failed,
        }
        await self._db.catalog_imports.insert_one(
            {**result, "query": query, "genre": genre, "started_at": started, "finished_at": utcnow()}
        )
        return result
