"""Report liked playlist targets: missing, low-quality, or preview-only."""

from __future__ import annotations

import asyncio
import json

from app.catalog.liked_music_match import (
    candidate_from_doc,
    is_acceptable_liked_match,
    score_candidate,
)


async def _best_saved(db, target):
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
    return best
from app.catalog.liked_music_seed import LIKED_MUSIC_ALL, PLAYLIST_ID
from app.config import get_settings
from app.database.client import close_mongodb, connect_mongodb, get_catalog_db


async def main() -> None:
    settings = get_settings()
    if not await connect_mongodb(settings.mongodb_uri, settings.mongodb_database):
        raise SystemExit("MongoDB unavailable")
    db = get_catalog_db()
    assert db is not None

    report: list[dict] = []
    missing = 0
    weak = 0
    preview = 0

    for target in LIKED_MUSIC_ALL:
        doc = await _best_saved(db, target)
        row = {"target_title": target.title, "target_artist": target.artist}
        if not doc:
            missing += 1
            row["status"] = "missing"
            report.append(row)
            continue
        cand = candidate_from_doc(doc)
        row.update(
            {
                "status": "ok" if is_acceptable_liked_match(target, cand) else "weak",
                "score": round(score_candidate(target, cand), 3),
                "catalog_title": doc.get("title"),
                "catalog_artist": (doc.get("artist") or {}).get("name"),
                "provider": (doc.get("source") or {}).get("provider"),
                "preview_only": bool((doc.get("playback") or {}).get("preview_only")),
            }
        )
        if row["status"] == "weak":
            weak += 1
        if row.get("preview_only"):
            preview += 1
        report.append(row)

    pl = await db.playlists.find_one({"slug": PLAYLIST_ID}) or {}
    print(
        json.dumps(
            {
                "targets": len(LIKED_MUSIC_ALL),
                "missing": missing,
                "weak": weak,
                "preview_only": preview,
                "playlist_track_ids": len(pl.get("track_ids") or []),
                "issues": [r for r in report if r.get("status") != "ok"],
            },
            indent=2,
        )
    )
    await close_mongodb()


if __name__ == "__main__":
    asyncio.run(main())
