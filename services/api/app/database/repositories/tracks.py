from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.catalog.normalize import dedupe_fingerprint, slugify


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def track_id_str(doc: dict[str, Any]) -> str:
    _id = doc.get("_id")
    return str(_id)


class TrackRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.tracks
        self._playback = db.playback_sources

    async def upsert_track(self, document: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Insert or update by _id if provided, else by dedupe_fingerprint."""
        now = utcnow()
        document.setdefault("created_at", now)
        document["updated_at"] = now
        if "dedupe_fingerprint" not in document:
            artist_name = (document.get("artist") or {}).get("name") or ""
            document["dedupe_fingerprint"] = dedupe_fingerprint(
                artist_name,
                document.get("title") or "",
                document.get("duration_seconds"),
            )
        if "slug" not in document and document.get("title"):
            document["slug"] = slugify(document["title"])

        track_id = document.get("_id")
        if track_id is not None:
            existing = await self._col.find_one({"_id": track_id})
            if existing:
                await self._col.update_one({"_id": track_id}, {"$set": document})
                merged = {**existing, **document}
                await self._sync_playback_source(merged)
                return merged, False
            await self._col.insert_one(document)
            await self._sync_playback_source(document)
            return document, True

        existing = await self._col.find_one({"dedupe_fingerprint": document["dedupe_fingerprint"]})
        if existing:
            await self._col.update_one({"_id": existing["_id"]}, {"$set": document})
            merged = {**existing, **document}
            await self._sync_playback_source(merged)
            return merged, False

        document["_id"] = ObjectId()
        await self._col.insert_one(document)
        await self._sync_playback_source(document)
        return document, True

    async def _sync_playback_source(self, track: dict[str, Any]) -> None:
        playback = track.get("playback") or {}
        source = track.get("source") or {}
        if not playback.get("available"):
            return
        provider = source.get("provider") or "local"
        provider_track_id = source.get("provider_track_id") or track_id_str(track)
        doc = {
            "track_id": track_id_str(track),
            "provider": provider,
            "provider_track_id": str(provider_track_id),
            "playback_type": playback.get("type") or "local",
            "stream_url": playback.get("stream_url"),
            "download_allowed": bool(playback.get("download_allowed", False)),
            "updated_at": utcnow(),
        }
        await self._playback.update_one(
            {"provider": provider, "provider_track_id": str(provider_track_id)},
            {"$set": doc, "$setOnInsert": {"created_at": utcnow()}},
            upsert=True,
        )

    async def get_by_id(self, track_id: str) -> Optional[dict[str, Any]]:
        try:
            oid = ObjectId(track_id)
            hit = await self._col.find_one({"_id": oid})
            if hit:
                return hit
        except Exception:
            pass
        return await self._col.find_one({"_id": track_id})

    async def list_tracks(
        self,
        *,
        limit: int = 50,
        skip: int = 0,
        playable_only: bool = False,
        genre: str | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if playable_only:
            query["playback.available"] = True
        if genre:
            query["genres"] = genre
        cursor = self._col.find(query).sort("discovery.trending_score", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def tracks_by_genre(
        self,
        slug: str,
        *,
        playable_only: bool = False,
        featured_first: bool = True,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"genres": slug}
        if playable_only:
            query["playback.available"] = True
        if featured_first:
            featured_q = {**query, "discovery.featured_artist": {"$exists": True}}
            featured = (
                await self._col.find(featured_q)
                .sort("discovery.trending_score", -1)
                .limit(500)
                .to_list(length=500)
            )
            rest_q = {**query, "discovery.featured_artist": {"$exists": False}}
            rest = (
                await self._col.find(rest_q)
                .sort("discovery.trending_score", -1)
                .limit(max(0, 500 - len(featured)))
                .to_list(length=500)
            )
            return featured + rest
        cursor = self._col.find(query).sort("discovery.trending_score", -1).limit(500)
        return await cursor.to_list(length=500)

    async def featured_tracks(
        self,
        *,
        limit: int = 48,
        genre: str | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {
            "playback.available": True,
            "discovery.featured_artist": {"$exists": True},
        }
        if genre:
            query["genres"] = genre
        cursor = self._col.find(query).sort("discovery.trending_score", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def trending(self, *, limit: int = 20) -> list[dict[str, Any]]:
        query = {"playback.available": True}
        cursor = self._col.find(query).sort("discovery.trending_score", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def new_releases(self, *, limit: int = 20) -> list[dict[str, Any]]:
        query = {"playback.available": True, "release_date": {"$ne": None}}
        cursor = self._col.find(query).sort("release_date", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def count(self, *, playable_only: bool = False) -> int:
        query: dict[str, Any] = {}
        if playable_only:
            query["playback.available"] = True
        return await self._col.count_documents(query)

    async def count_by_provider(self) -> dict[str, int]:
        pipeline = [{"$group": {"_id": "$source.provider", "count": {"$sum": 1}}}]
        out: dict[str, int] = {}
        async for row in self._col.aggregate(pipeline):
            out[str(row["_id"] or "unknown")] = int(row["count"])
        return out
