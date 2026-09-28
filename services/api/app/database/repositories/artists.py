from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.catalog.normalize import slugify


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ArtistRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.artists

    async def upsert_by_name(
        self,
        name: str,
        *,
        genres: list[str] | None = None,
        musicbrainz_id: str | None = None,
        image_url: str | None = None,
        country: str | None = None,
    ) -> dict[str, Any]:
        slug = slugify(name)
        now = utcnow()
        existing = await self._col.find_one({"slug": slug})
        if existing:
            updates: dict[str, Any] = {"updated_at": now, "name": name}
            if genres:
                updates["genres"] = sorted(set((existing.get("genres") or []) + genres))
            if musicbrainz_id:
                updates["musicbrainz_id"] = musicbrainz_id
            if image_url:
                updates["image_url"] = image_url
            if country:
                updates["country"] = country
            await self._col.update_one({"_id": existing["_id"]}, {"$set": updates})
            existing.update(updates)
            return existing

        doc: dict[str, Any] = {
            "_id": ObjectId(),
            "name": name,
            "slug": slug,
            "genres": genres or [],
            "external_ids": {},
            "followers_count": 0,
            "verified": False,
            "created_at": now,
            "updated_at": now,
        }
        if image_url:
            doc["image_url"] = image_url
        if country:
            doc["country"] = country
        if musicbrainz_id:
            doc["musicbrainz_id"] = musicbrainz_id
        await self._col.insert_one(doc)
        return doc

    async def get_by_id(self, artist_id: str | ObjectId) -> Optional[dict[str, Any]]:
        oid = ObjectId(artist_id) if not isinstance(artist_id, ObjectId) else artist_id
        try:
            return await self._col.find_one({"_id": oid})
        except Exception:
            return None

    async def list_artists(self, *, limit: int = 50, skip: int = 0) -> list[dict[str, Any]]:
        cursor = self._col.find().sort("name", 1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def count(self) -> int:
        return await self._col.count_documents({})
