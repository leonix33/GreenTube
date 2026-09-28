"""Mark Deezer / preview-only bindings as non-streamable so imports prefer full sources."""

from __future__ import annotations

import asyncio
import json
import sys

from app.config import get_settings
from app.database.client import close_mongodb, connect_mongodb, get_catalog_db


async def main() -> None:
    settings = get_settings()
    if settings.allow_preview_playback:
        print(
            "ALLOW_PREVIEW_PLAYBACK is true — set false in .env for full-length-only catalog.",
            file=sys.stderr,
        )
    if not await connect_mongodb(settings.mongodb_uri, settings.mongodb_database):
        raise SystemExit("MongoDB unavailable")

    db = get_catalog_db()
    assert db is not None

    query = {
        "$or": [
            {"playback.preview_only": True},
            {"source.provider": "deezer"},
        ],
        "playback.available": True,
    }
    cursor = db.tracks.find(query, {"title": 1, "artist.name": 1, "playback": 1, "source": 1})
    ids = []
    async for doc in cursor:
        ids.append(doc["_id"])

    if not ids:
        print(json.dumps({"cleared": 0}))
        await close_mongodb()
        return

    result = await db.tracks.update_many(
        {"_id": {"$in": ids}},
        {
            "$set": {"playback.available": False, "playback.preview_only": True},
            "$unset": {"playback.stream_url": "", "playback.resolved_via": ""},
        },
    )
    print(json.dumps({"matched": len(ids), "modified": result.modified_count}))
    await close_mongodb()


if __name__ == "__main__":
    asyncio.run(main())
