from __future__ import annotations

from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.catalog.normalize import dedupe_fingerprint


async def find_existing_track(db: AsyncIOMotorDatabase, normalized: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Resolve duplicates in priority order:
    1. ISRC
    2. provider + provider_track_id
    3. MusicBrainz recording ID
    4. normalized artist + title + duration
    """
    identifiers = normalized.get("identifiers") or {}
    isrc = identifiers.get("isrc")
    if isrc:
        hit = await db.tracks.find_one({"identifiers.isrc": isrc})
        if hit:
            return hit

    source = normalized.get("source") or {}
    provider = source.get("provider")
    provider_track_id = source.get("provider_track_id")
    if provider and provider_track_id:
        hit = await db.tracks.find_one(
            {"source.provider": provider, "source.provider_track_id": str(provider_track_id)}
        )
        if hit:
            return hit

    mbid = identifiers.get("musicbrainz_recording_id")
    if mbid:
        hit = await db.tracks.find_one({"identifiers.musicbrainz_recording_id": mbid})
        if hit:
            return hit

    artist_name = (normalized.get("artist") or {}).get("name") or ""
    title = normalized.get("title") or ""
    duration_seconds = normalized.get("duration_seconds")
    fp = dedupe_fingerprint(artist_name, title, duration_seconds)
    hit = await db.tracks.find_one({"dedupe_fingerprint": fp})
    if hit:
        return hit

    return None
