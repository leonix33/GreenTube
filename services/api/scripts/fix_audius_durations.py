"""Fix duration_seconds on Audius tracks imported with the old ms÷1000 bug."""

from __future__ import annotations

import asyncio

import httpx

from app.config import get_settings
from app.database.client import close_mongodb, connect_mongodb, get_catalog_db


async def main() -> None:
    settings = get_settings()
    if not await connect_mongodb(settings.mongodb_uri, settings.mongodb_database):
        raise SystemExit("MongoDB unavailable")
    db = get_catalog_db()
    assert db is not None
    updated = 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        root = (await client.get("https://api.audius.co")).json().get("data", ["https://api.audius.co"])[0]
        root = str(root).rstrip("/")
        if not root.startswith("http"):
            root = f"https://{root}"
        cursor = db.tracks.find(
            {
                "source.provider": "audius",
                "$or": [
                    {"duration_seconds": {"$in": [None, 0]}},
                    {"duration_seconds": {"$lt": 1}},
                ],
            }
        )
        async for doc in cursor:
            tid = (doc.get("source") or {}).get("provider_track_id")
            if not tid:
                continue
            try:
                resp = await client.get(f"{root}/v1/tracks/{tid}")
                resp.raise_for_status()
                row = resp.json().get("data") or {}
                d = int(row.get("duration") or 0)
                seconds = d // 1000 if d > 10_000 else d
                if seconds <= 0:
                    continue
                await db.tracks.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"duration_seconds": seconds}},
                )
                updated += 1
            except Exception:
                continue
    print({"duration_fields_fixed": updated})
    await close_mongodb()


if __name__ == "__main__":
    asyncio.run(main())
