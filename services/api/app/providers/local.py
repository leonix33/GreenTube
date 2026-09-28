from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.catalog.normalize import dedupe_fingerprint, slugify
from app.catalog_seed import SEED_TRACKS, ensure_demo_audio
from app.providers.base import CatalogProvider


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LocalCatalogProvider(CatalogProvider):
    name = "local"

    def _seed_to_track_doc(self, item) -> dict[str, Any]:
        ensure_demo_audio()
        duration_seconds = max(1, int(item.duration_ms / 1000))
        artist_name = item.artist
        title = item.title
        return {
            "_id": item.id,
            "title": title,
            "slug": slugify(title),
            "artist": {"id": None, "name": artist_name},
            "album": {"id": None, "title": item.album},
            "genres": list(item.genres),
            "duration_seconds": duration_seconds,
            "release_date": None,
            "explicit": False,
            "artwork_url": None,
            "identifiers": {"isrc": None, "musicbrainz_recording_id": None},
            "source": {
                "provider": "local",
                "provider_track_id": item.filename,
                "provider_url": item.stream_path,
            },
            "playback": {
                "available": True,
                "type": "local",
                "stream_url": item.stream_path,
                "download_allowed": False,
            },
            "stats": {"plays": 0, "likes": 0, "skips": 0, "completions": 0},
            "discovery": {"trending_score": 0.0, "breakout_score": 0.0},
            "dedupe_fingerprint": dedupe_fingerprint(artist_name, title, duration_seconds),
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }

    async def search_tracks(self, query: str, *, limit: int = 25) -> list[dict[str, Any]]:
        q = query.lower()
        hits = [
            self._seed_to_track_doc(t)
            for t in SEED_TRACKS
            if q in t.title.lower() or q in t.artist.lower() or q in t.album.lower()
        ]
        return hits[:limit]

    async def import_tracks(
        self,
        *,
        query: str | None = None,
        genre: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        items = SEED_TRACKS
        if genre:
            items = [t for t in items if genre in t.genres]
        if query:
            q = query.lower()
            items = [
                t
                for t in items
                if q in t.title.lower() or q in t.artist.lower() or q in t.album.lower()
            ]
        return [self._seed_to_track_doc(t) for t in items[:limit]]
