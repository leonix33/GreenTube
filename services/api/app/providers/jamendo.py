from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.catalog.normalize import dedupe_fingerprint, slugify
from app.config import get_settings
from app.providers.base import CatalogProvider

JAMENDO_BASE = "https://api.jamendo.com/v3.0"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JamendoCatalogProvider(CatalogProvider):
    name = "jamendo"

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def configured(self) -> bool:
        return bool(self._settings.jamendo_client_id)

    def _normalize_track(self, row: dict[str, Any]) -> dict[str, Any]:
        title = row.get("name") or "Untitled"
        artist_name = row.get("artist_name") or "Unknown artist"
        duration_seconds = int(row.get("duration") or 0) or None
        track_id = str(row.get("id"))
        audio = row.get("audio") or row.get("audiodownload") or ""
        download_allowed = bool(row.get("audiodownload_allowed"))
        tags = row.get("musicinfo", {}).get("tags", {}).get("genres") or row.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split() if t.strip()]
        genres = [str(t).lower().replace(" ", "-") for t in tags][:8]

        return {
            "title": title,
            "slug": slugify(title),
            "artist": {"id": None, "name": artist_name},
            "album": {"id": None, "title": row.get("album_name")},
            "genres": genres,
            "duration_seconds": duration_seconds,
            "release_date": row.get("releasedate"),
            "explicit": False,
            "artwork_url": row.get("image"),
            "identifiers": {"isrc": None, "musicbrainz_recording_id": None},
            "source": {
                "provider": "jamendo",
                "provider_track_id": track_id,
                "provider_url": row.get("shareurl") or row.get("shorturl"),
            },
            "playback": {
                "available": bool(audio),
                "type": "remote_stream",
                "stream_url": audio,
                "download_allowed": download_allowed,
            },
            "stats": {"plays": 0, "likes": 0, "skips": 0, "completions": 0},
            "discovery": {"trending_score": float(row.get("stats_rate_week") or 0)},
            "dedupe_fingerprint": dedupe_fingerprint(artist_name, title, duration_seconds),
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }

    async def search_tracks(self, query: str, *, limit: int = 25) -> list[dict[str, Any]]:
        if not self.configured:
            return []
        params = {
            "client_id": self._settings.jamendo_client_id,
            "format": "json",
            "limit": min(limit, 200),
            "search": query,
            "include": "musicinfo",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{JAMENDO_BASE}/tracks/", params=params)
            resp.raise_for_status()
            rows = resp.json().get("results", [])
        return [self._normalize_track(r) for r in rows if r.get("audio")]

    async def import_tracks(
        self,
        *,
        query: str | None = None,
        genre: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        if not self.configured:
            return []
        target = max(1, min(limit, 2000))
        page_size = 200
        collected: list[dict[str, Any]] = []
        offset = 0

        async with httpx.AsyncClient(timeout=60.0) as client:
            while len(collected) < target:
                params: dict[str, Any] = {
                    "client_id": self._settings.jamendo_client_id,
                    "format": "json",
                    "limit": min(page_size, target - len(collected)),
                    "offset": offset,
                    "include": "musicinfo",
                }
                if genre:
                    params["tags"] = genre
                if query:
                    params["search"] = query
                resp = await client.get(f"{JAMENDO_BASE}/tracks/", params=params)
                resp.raise_for_status()
                rows = resp.json().get("results", [])
                if not rows:
                    break
                page = [self._normalize_track(r) for r in rows if r.get("audio")]
                if genre:
                    for track in page:
                        if genre not in track["genres"]:
                            track["genres"].append(genre)
                collected.extend(page)
                offset += len(rows)
                if len(rows) < page_size:
                    break

        return collected[:target]
