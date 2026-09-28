"""Deezer public API — 30s preview streams for major-label catalog (no API key required)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.catalog.normalize import dedupe_fingerprint, slugify
from app.providers.base import CatalogProvider

DEEZER_API = "https://api.deezer.com"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DeezerCatalogProvider(CatalogProvider):
    name = "deezer"

    def _normalize_track(self, row: dict[str, Any]) -> dict[str, Any]:
        title = row.get("title") or "Untitled"
        artist_name = (row.get("artist") or {}).get("name") or "Unknown artist"
        duration_seconds = int(row.get("duration") or 0) or None
        track_id = str(row.get("id"))
        preview = (row.get("preview") or "").strip()
        album = row.get("album") or {}
        explicit = bool(row.get("explicit_lyrics"))

        return {
            "title": title,
            "slug": slugify(title),
            "artist": {"id": None, "name": artist_name},
            "album": {"id": None, "title": album.get("title")},
            "genres": [],
            "duration_seconds": duration_seconds,
            "release_date": None,
            "explicit": explicit,
            "artwork_url": (album.get("cover_medium") or album.get("cover")),
            "identifiers": {"isrc": row.get("isrc"), "musicbrainz_recording_id": None},
            "source": {
                "provider": "deezer",
                "provider_track_id": track_id,
                "provider_url": row.get("link"),
            },
            "playback": {
                "available": bool(preview),
                "type": "remote_stream",
                "stream_url": preview,
                "download_allowed": False,
                "preview_only": True,
            },
            "stats": {"plays": 0, "likes": 0, "skips": 0, "completions": 0},
            "discovery": {"trending_score": float(row.get("rank") or 0)},
            "dedupe_fingerprint": dedupe_fingerprint(artist_name, title, duration_seconds),
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }

    async def search_tracks(self, query: str, *, limit: int = 25) -> list[dict[str, Any]]:
        return await self.import_tracks(query=query, limit=limit)

    async def import_tracks(
        self,
        *,
        query: str | None = None,
        genre: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        if not query:
            return []
        target = max(1, min(limit, 100))
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{DEEZER_API}/search", params={"q": query, "limit": target})
            resp.raise_for_status()
            rows = resp.json().get("data") or []
        out: list[dict[str, Any]] = []
        for row in rows:
            track = self._normalize_track(row)
            if genre and genre not in track["genres"]:
                track["genres"].append(genre)
            if track["playback"]["available"]:
                out.append(track)
        return out[:target]
