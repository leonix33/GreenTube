from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.catalog_seed import GENRES


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GenreRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.genres
        self._tracks = db.tracks

    async def sync_taxonomy_from_seed(self) -> None:
        """Ensure browse genres exist (from catalog_seed taxonomy)."""
        now = utcnow()
        for genre in GENRES:
            await self._col.update_one(
                {"slug": genre.slug},
                {
                    "$set": {"name": genre.name, "updated_at": now},
                    "$setOnInsert": {"slug": genre.slug, "created_at": now},
                },
                upsert=True,
            )

    async def refresh_track_counts(self) -> None:
        pipeline = [
            {"$unwind": "$genres"},
            {"$group": {"_id": "$genres", "count": {"$sum": 1}}},
        ]
        counts: dict[str, int] = {}
        async for row in self._tracks.aggregate(pipeline):
            counts[str(row["_id"])] = int(row["count"])

        async for doc in self._col.find({}):
            slug = doc.get("slug")
            await self._col.update_one(
                {"_id": doc["_id"]},
                {"$set": {"track_count": counts.get(slug, 0), "updated_at": utcnow()}},
            )

    async def list_genres(self) -> list[dict[str, Any]]:
        cursor = self._col.find().sort("name", 1)
        return await cursor.to_list(length=500)

    async def count(self) -> int:
        return await self._col.count_documents({})
