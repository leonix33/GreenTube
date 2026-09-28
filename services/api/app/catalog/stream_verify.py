"""Verify provider candidates expose a working full-length stream."""

from __future__ import annotations

from app.catalog.playback_resolve import _bytes_ok, _fresh_audius_stream
from app.config import get_settings


async def attach_verified_stream(candidate: dict) -> dict | None:
    source = candidate.get("source") or {}
    provider = source.get("provider") or ""
    playback = candidate.get("playback") or {}

    if provider == "deezer":
        if not get_settings().allow_preview_playback:
            return None
        url = playback.get("stream_url")
        if url and await _bytes_ok(url):
            out = dict(candidate)
            out["playback"] = {**playback, "preview_only": True}
            return out
        return None

    if provider == "audius":
        tid = source.get("provider_track_id")
        if not tid:
            return None
        url = await _fresh_audius_stream(str(tid))
        if not url:
            return None
        out = dict(candidate)
        out["playback"] = {
            **playback,
            "available": True,
            "stream_url": url,
            "preview_only": False,
            "type": "remote_stream",
        }
        return out

    if provider == "jamendo":
        url = playback.get("stream_url")
        if url and await _bytes_ok(url):
            out = dict(candidate)
            out["playback"] = {**playback, "preview_only": False}
            return out
        return None

    if provider == "local" and playback.get("stream_url"):
        return candidate

    url = playback.get("stream_url")
    if url and await _bytes_ok(url):
        out = dict(candidate)
        out.setdefault("playback", {})["preview_only"] = False
        return out
    return None


async def filter_verified_candidates(candidates: list[dict]) -> list[dict]:
    verified: list[dict] = []
    seen: set[str] = set()
    for raw in candidates:
        ok = await attach_verified_stream(raw)
        if not ok:
            continue
        key = (
            (ok.get("source") or {}).get("provider"),
            (ok.get("source") or {}).get("provider_track_id"),
            ok.get("title"),
        )
        if key in seen:
            continue
        seen.add(key)
        verified.append(ok)
    return verified
