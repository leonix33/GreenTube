from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.catalog.normalize import slugify


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AlbumRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.albums

    async def upsert_by_title_artist(
        self,
        title: str,
        artist_id: ObjectId,
        *,
        genres: list[str] | None = None,
        artwork_url: str | None = None,
        release_date: str | None = None,
        musicbrainz_release_id: str | None = None,
    ) -> dict[str, Any]:
        slug = slugify(f"{title}-{str(artist_id)}")
        now = utcnow()
        existing = await self._col.find_one({"slug": slug})
        if existing:
            updates: dict[str, Any] = {"updated_at": now, "title": title, "artist_id": artist_id}
            if genres:
                updates["genres"] = sorted(set((existing.get("genres") or []) + genres))
            if artwork_url:
                updates["artwork_url"] = artwork_url
            if release_date:
                updates["release_date"] = release_date
            if musicbrainz_release_id:
                updates["musicbrainz_release_id"] = musicbrainz_release_id
            await self._col.update_one({"_id": existing["_id"]}, {"$set": updates})
            existing.update(updates)
            return existing

        doc = {
            "_id": ObjectId(),
            "title": title,
            "slug": slug,
            "artist_id": artist_id,
            "artwork_url": artwork_url,
            "release_date": release_date,
            "genres": genres or [],
            "musicbrainz_release_id": musicbrainz_release_id,
            "track_count": 0,
            "created_at": now,
            "updated_at": now,
        }
        await self._col.insert_one(doc)
        return doc

    async def get_by_id(self, album_id: str | ObjectId) -> Optional[dict[str, Any]]:
        oid = ObjectId(album_id) if not isinstance(album_id, ObjectId) else album_id
        try:
            return await self._col.find_one({"_id": oid})
        except Exception:
            return None

    async def list_albums(self, *, limit: int = 50, skip: int = 0) -> list[dict[str, Any]]:
        cursor = self._col.find().sort("title", 1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def count(self) -> int:
        return await self._col.count_documents({})
