"""Keep one best catalog row per liked target; rebuild playlist order."""

from __future__ import annotations

import asyncio

from app.catalog.liked_music_match import candidate_from_doc, score_candidate
from datetime import datetime, timezone

from app.catalog.liked_music_seed import (
    LIKED_MUSIC_ALL,
    PLAYLIST_DESCRIPTION,
    PLAYLIST_ID,
    PLAYLIST_TITLE,
)
from app.config import get_settings
from app.database.client import close_mongodb, connect_mongodb, get_catalog_db


def _utcnow():
    return datetime.now(timezone.utc)


async def _find_saved(db, target):
    from app.catalog.liked_music_match import candidate_from_doc, score_candidate

    best = None
    best_s = 0.0
    query = {
        "discovery.liked_music_target.title": target.title,
        "discovery.liked_music_target.artist": target.artist,
        "playback.available": True,
    }
    async for doc in db.tracks.find(query):
        s = score_candidate(target, candidate_from_doc(doc))
        if s > best_s:
            best_s = s
            best = doc
    return best if best_s >= 0.5 else None


async def _clear_other_liked_bindings(db, target, keep_id) -> None:
    await db.tracks.update_many(
        {
            "discovery.liked_music_target.title": target.title,
            "discovery.liked_music_target.artist": target.artist,
            "_id": {"$ne": keep_id},
        },
        {
            "$unset": {
                "discovery.liked_music_target": "",
                "discovery.playlist_liked_music": "",
            }
        },
    )


async def _save_playlist(db, track_ids: list[str]) -> None:
    await db.playlists.update_one(
        {"slug": PLAYLIST_ID},
        {
            "$set": {
                "slug": PLAYLIST_ID,
                "title": PLAYLIST_TITLE,
                "description": PLAYLIST_DESCRIPTION,
                "parts": {"1": track_ids},
                "track_ids": track_ids,
                "updated_at": _utcnow(),
            },
            "$setOnInsert": {"created_at": _utcnow(), "source": "liked_music_import"},
        },
        upsert=True,
    )


async def main() -> None:
    settings = get_settings()
    if not await connect_mongodb(settings.mongodb_uri, settings.mongodb_database):
        raise SystemExit("MongoDB unavailable")
    db = get_catalog_db()
    assert db is not None

    ordered_ids: list[str] = []
    for target in LIKED_MUSIC_ALL:
        saved = await _find_saved(db, target)
        if not saved:
            continue
        await _clear_other_liked_bindings(db, target, saved["_id"])
        ordered_ids.append(str(saved["_id"]))

    await _save_playlist(db, ordered_ids)
    print(f"playlist {PLAYLIST_ID}: {len(ordered_ids)} tracks (from {len(LIKED_MUSIC_ALL)} targets)")

    await close_mongodb()


if __name__ == "__main__":
    asyncio.run(main())
