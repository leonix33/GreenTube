from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from app.catalog.normalize import dedupe_fingerprint, slugify
from app.config import get_settings
from app.providers.base import CatalogProvider

MB_BASE = "https://musicbrainz.org/ws/2"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MusicBrainzCatalogProvider(CatalogProvider):
    name = "musicbrainz"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._last_request_at = 0.0

    async def _rate_limit(self) -> None:
        # MusicBrainz asks for ~1 req/sec for anonymous clients.
        now = asyncio.get_event_loop().time()
        wait = 1.1 - (now - self._last_request_at)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_request_at = asyncio.get_event_loop().time()

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        await self._rate_limit()
        headers = {
            "User-Agent": self._settings.musicbrainz_user_agent,
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            resp = await client.get(f"{MB_BASE}{path}", params={**params, "fmt": "json"})
            resp.raise_for_status()
            return resp.json()

    def _normalize_recording(self, rec: dict[str, Any]) -> dict[str, Any]:
        title = rec.get("title") or "Unknown recording"
        artist_credit = rec.get("artist-credit") or []
        artist_name = "Unknown artist"
        if artist_credit:
            artist_name = artist_credit[0].get("name") or artist_name
        length_ms = rec.get("length")
        duration_seconds = int(length_ms / 1000) if length_ms else None
        mbid = rec.get("id")
        isrcs = []
        for isrc_block in rec.get("isrcs") or []:
            if isinstance(isrc_block, str):
                isrcs.append(isrc_block)
        isrc = isrcs[0] if isrcs else None

        return {
            "title": title,
            "slug": slugify(title),
            "artist": {"id": None, "name": artist_name},
            "album": {"id": None, "title": None},
            "genres": [],
            "duration_seconds": duration_seconds,
            "release_date": None,
            "explicit": False,
            "artwork_url": None,
            "identifiers": {
                "isrc": isrc,
                "musicbrainz_recording_id": mbid,
            },
            "source": {
                "provider": "musicbrainz",
                "provider_track_id": mbid,
                "provider_url": f"https://musicbrainz.org/recording/{mbid}",
            },
            "playback": {
                "available": False,
                "type": "metadata_only",
                "stream_url": None,
                "download_allowed": False,
            },
            "stats": {"plays": 0, "likes": 0, "skips": 0, "completions": 0},
            "discovery": {"trending_score": 0.0, "breakout_score": 0.0},
            "dedupe_fingerprint": dedupe_fingerprint(artist_name, title, duration_seconds),
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }

    async def search_tracks(self, query: str, *, limit: int = 25) -> list[dict[str, Any]]:
        data = await self._get("/recording", {"query": query, "limit": min(limit, 100)})
        return [self._normalize_recording(r) for r in data.get("recordings", [])]

    async def import_tracks(
        self,
        *,
        query: str | None = None,
        genre: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        q = query or "recording:*"
        if genre:
            q = f'{q} AND tag:{genre}'
        return await self.search_tracks(q, limit=limit)
