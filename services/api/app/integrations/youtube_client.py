"""YouTube Data API — official music video lookup (embed playback in the web app)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import get_settings

YOUTUBE_API = "https://www.googleapis.com/youtube/v3"


def configured() -> bool:
    return bool(get_settings().youtube_api_key)


def _clean_title(title: str) -> str:
    t = re.sub(
        r"\(official( music)? video\)|\[official( music)? video\]|official video|lyrics|visualizer",
        "",
        title,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", t).strip()


async def search_music_video_id(*, title: str, artist: str) -> str | None:
    """Return a YouTube video id for an official-style music video, if API key is set."""
    if not configured():
        return None
    key = get_settings().youtube_api_key
    q = f"{artist} {_clean_title(title)} official music video"
    params = {
        "part": "snippet",
        "type": "video",
        "videoCategoryId": "10",
        "maxResults": 8,
        "q": q,
        "key": key,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(f"{YOUTUBE_API}/search?{urlencode(params)}")
        resp.raise_for_status()
        items = resp.json().get("items") or []

    artist_key = artist.lower().split()[0] if artist else ""
    title_key = _clean_title(title).lower()
    for item in items:
        vid = (item.get("id") or {}).get("videoId")
        sn = item.get("snippet") or {}
        vtitle = (sn.get("title") or "").lower()
        channel = (sn.get("channelTitle") or "").lower()
        if not vid:
            continue
        if artist_key and artist_key not in vtitle and artist_key not in channel:
            if title_key.split()[0] not in vtitle:
                continue
        if "official" in vtitle or artist_key in channel:
            return vid
    if items:
        vid = (items[0].get("id") or {}).get("videoId")
        return str(vid) if vid else None
    return None


def embed_url(video_id: str) -> str:
    return f"https://www.youtube.com/embed/{video_id}"
