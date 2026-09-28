"""Spotify Web API (OAuth + catalog search)."""

from __future__ import annotations

import base64
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import get_settings

SPOTIFY_ACCOUNTS = "https://accounts.spotify.com"
SPOTIFY_API = "https://api.spotify.com/v1"

SCOPES = (
    "streaming user-read-email user-read-private user-modify-playback-state "
    "user-read-playback-state"
)


def configured() -> bool:
    s = get_settings()
    return bool(s.spotify_client_id and s.spotify_client_secret)


def authorize_url(*, state: str) -> str:
    s = get_settings()
    params = {
        "client_id": s.spotify_client_id,
        "response_type": "code",
        "redirect_uri": s.spotify_redirect_uri,
        "scope": SCOPES,
        "state": state,
        "show_dialog": "false",
    }
    return f"{SPOTIFY_ACCOUNTS}/authorize?{urlencode(params)}"


async def exchange_code(code: str) -> dict[str, Any]:
    s = get_settings()
    auth = base64.b64encode(f"{s.spotify_client_id}:{s.spotify_client_secret}".encode()).decode()
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            f"{SPOTIFY_ACCOUNTS}/api/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": s.spotify_redirect_uri,
            },
            headers={"Authorization": f"Basic {auth}"},
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    s = get_settings()
    auth = base64.b64encode(f"{s.spotify_client_id}:{s.spotify_client_secret}".encode()).decode()
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            f"{SPOTIFY_ACCOUNTS}/api/token",
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            headers={"Authorization": f"Basic {auth}"},
        )
        resp.raise_for_status()
        return resp.json()


def expires_at_from_token(payload: dict[str, Any]) -> datetime:
    sec = int(payload.get("expires_in") or 3600)
    return datetime.now(timezone.utc) + timedelta(seconds=max(60, sec - 60))


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s.lower()).strip()


async def search_track(
    access_token: str,
    *,
    title: str,
    artist: str,
) -> dict[str, Any] | None:
    q = f"track:{title} artist:{artist}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            f"{SPOTIFY_API}/search",
            params={"q": q, "type": "track", "limit": 10},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        items = resp.json().get("tracks", {}).get("items") or []

    nt, na = _norm(title), _norm(artist)
    best: dict[str, Any] | None = None
    best_score = 0.0
    for item in items:
        name = _norm(item.get("name") or "")
        artists = " ".join(_norm(a.get("name") or "") for a in item.get("artists") or [])
        if na not in artists and not any(p in artists for p in na.split() if len(p) > 2):
            continue
        score = 0.0
        if nt == name:
            score = 1.0
        elif nt in name or name in nt:
            score = 0.85
        else:
            tt = set(nt.split())
            score = len(tt & set(name.split())) / max(len(tt), 1)
        if score > best_score:
            best_score = score
            best = item
    if best_score < 0.55 or not best:
        return None
    return best
