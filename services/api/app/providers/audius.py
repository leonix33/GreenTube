from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.catalog.normalize import dedupe_fingerprint, slugify
from app.providers.base import CatalogProvider

AUDIUS_API_ROOT = "https://api.audius.co"
AUDIUS_HOST = "api.audius.co"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AudiusCatalogProvider(CatalogProvider):
    name = "audius"

    async def _api_root(self, client: httpx.AsyncClient) -> str:
        resp = await client.get(AUDIUS_API_ROOT, timeout=20.0)
        resp.raise_for_status()
        hosts = resp.json().get("data") or [AUDIUS_API_ROOT]
        base = str(hosts[0]).rstrip("/")
        return base if base.startswith("http") else f"https://{base}"

    def _normalize_track(self, row: dict[str, Any], api_root: str) -> dict[str, Any]:
        title = row.get("title") or "Untitled"
        artist_name = (row.get("user") or {}).get("name") or "Unknown artist"
        raw_duration = row.get("duration")
        if raw_duration is None:
            duration_seconds = None
        else:
            d = int(raw_duration)
            # Audius API returns seconds (not ms); guard legacy ms values.
            duration_seconds = d // 1000 if d > 10_000 else d
            if duration_seconds <= 0:
                duration_seconds = None
        track_id = str(row.get("id"))
        stream_url = f"{api_root}/v1/tracks/{track_id}/stream"
        genres = [str(g).lower().replace(" ", "-") for g in (row.get("genre") and [row.get("genre")] or [])]
        tag_blob = str(row.get("tags") or "")
        for token in tag_blob.replace(",", " ").split():
            slug = token.strip().lower().replace(" ", "-")
            if slug and slug not in genres:
                genres.append(slug)

        return {
            "title": title,
            "slug": slugify(title),
            "artist": {"id": None, "name": artist_name},
            "album": {"id": None, "title": None},
            "genres": genres,
            "duration_seconds": duration_seconds,
            "release_date": row.get("release_date"),
            "explicit": bool(row.get("isrc") is None and row.get("ddex_app") is None),
            "artwork_url": (row.get("artwork") or {}).get("1000x1000"),
            "identifiers": {"isrc": row.get("isrc"), "musicbrainz_recording_id": None},
            "source": {
                "provider": "audius",
                "provider_track_id": track_id,
                "provider_url": f"https://audius.co/tracks/{track_id}",
            },
            "playback": {
                "available": True,
                "type": "remote_stream",
                "stream_url": stream_url,
                "download_allowed": False,
            },
            "stats": {"plays": int(row.get("play_count") or 0), "likes": 0, "skips": 0, "completions": 0},
            "discovery": {"trending_score": float(row.get("play_count") or 0)},
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
        target = max(1, min(limit, 2000))
        page_size = 100
        collected: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        offset = 0

        async with httpx.AsyncClient(timeout=60.0) as client:
            api_root = await self._api_root(client)
            while len(collected) < target:
                params: dict[str, Any] = {
                    "limit": min(page_size, target - len(collected)),
                    "offset": offset,
                    "app_name": "GreenTube",
                }
                if query:
                    params["query"] = query
                # Audius `genre` filter uses a fixed enum — use text search + tag our catalog slug.
                resp = await client.get(f"{api_root}/v1/tracks/search", params=params)
                resp.raise_for_status()
                rows = resp.json().get("data") or []
                if not rows:
                    break
                for row in rows:
                    track_id = str(row.get("id"))
                    if track_id in seen_ids:
                        continue
                    seen_ids.add(track_id)
                    track = self._normalize_track(row, api_root)
                    if genre and genre not in track["genres"]:
                        track["genres"].append(genre)
                    collected.append(track)
                    if len(collected) >= target:
                        break
                offset += len(rows)
                if len(rows) < page_size:
                    break

        return collected[:target]
