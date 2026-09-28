"""Resolve a playable stream URL (refresh provider links, Deezer fallback)."""

from __future__ import annotations

import httpx

from app.config import get_settings
from app.providers.audius import AudiusCatalogProvider
from app.providers.deezer import DeezerCatalogProvider


async def _bytes_ok(url: str, *, timeout: float = 5.0) -> bool:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers={"Range": "bytes=0-1024"})
            return resp.status_code in (200, 206) and len(resp.content) > 0
    except Exception:
        return False


async def _fresh_deezer_preview(provider_track_id: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"https://api.deezer.com/track/{provider_track_id}")
            resp.raise_for_status()
            preview = (resp.json() or {}).get("preview") or ""
            return preview.strip() or None
    except Exception:
        return None


async def _deezer_search_fallback(doc: dict) -> str | None:
    discovery = doc.get("discovery") or {}
    target = discovery.get("liked_music_target") or {}
    artist = target.get("artist") or (doc.get("artist") or {}).get("name") or ""
    title = target.get("title") or doc.get("title") or ""
    if not artist or not title:
        return None
    dz = DeezerCatalogProvider()
    hits = await dz.import_tracks(query=f"{artist} {title}", limit=8)
    artist_key = artist.lower().split()[0]
    title_key = title.lower().split()[0]
    for hit in hits:
        ht = (hit.get("title") or "").lower()
        ha = ((hit.get("artist") or {}).get("name") or "").lower()
        if title_key in ht and (artist_key in ha or artist.lower() in ht):
            url = (hit.get("playback") or {}).get("stream_url")
            if url:
                return url
    if hits:
        url = (hits[0].get("playback") or {}).get("stream_url")
        return url or None
    return None


async def _fresh_audius_stream(provider_track_id: str) -> str | None:
    audius = AudiusCatalogProvider()
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            root = await audius._api_root(client)
            url = f"{root.rstrip('/')}/v1/tracks/{provider_track_id}/stream"
            if await _bytes_ok(url, timeout=6.0):
                return url
    except Exception:
        return None
    return None


async def resolve_playback_stream(doc: dict) -> str | None:
    settings = get_settings()
    previews_ok = settings.allow_preview_playback
    playback = doc.get("playback") or {}
    if not playback.get("available"):
        return None
    source = doc.get("source") or {}
    provider = source.get("provider") or "local"
    url = (playback.get("stream_url") or "").strip()
    provider_track_id = source.get("provider_track_id")

    if provider == "audius" and provider_track_id:
        fresh = await _fresh_audius_stream(str(provider_track_id))
        if fresh:
            return fresh

    if provider == "deezer":
        if not previews_ok:
            return None
        if provider_track_id:
            fresh = await _fresh_deezer_preview(str(provider_track_id))
            if fresh:
                return fresh

    if url and await _bytes_ok(url, timeout=4.0):
        if provider == "deezer" and not previews_ok:
            return None
        return url

    if previews_ok:
        fallback = await _deezer_search_fallback(doc)
        return fallback or None
    return None
