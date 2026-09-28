"""Spotify OAuth + player token + Liked catalog matching."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Cookie, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.catalog.liked_music_seed import LIKED_MUSIC_ALL
from app.config import get_settings
from app.database.client import get_catalog_db
from app.integrations.spotify_client import (
    authorize_url,
    configured,
    exchange_code,
    expires_at_from_token,
    refresh_access_token,
    search_track,
)
from app.integrations.spotify_session import spotify_tokens, upsert_spotify_tokens

router = APIRouter(prefix="/integrations/spotify", tags=["spotify"])


def _frontend_redirect(path: str = "/liked") -> str:
    base = get_settings().frontend_url.rstrip("/")
    return f"{base}{path}"


async def _valid_access_token(session_id: str) -> str | None:
    db = get_catalog_db()
    if db is None or not session_id:
        return None
    spotify = await spotify_tokens(db, session_id)
    if not spotify:
        return None
    access = spotify.get("access_token")
    expires_at: datetime | None = spotify.get("expires_at")
    if access and expires_at and expires_at > datetime.now(timezone.utc):
        return access
    refresh = spotify.get("refresh_token")
    if not refresh:
        return None
    payload = await refresh_access_token(refresh)
    access = payload["access_token"]
    await upsert_spotify_tokens(
        db,
        session_id,
        access_token=access,
        refresh_token=payload.get("refresh_token") or refresh,
        expires_at=expires_at_from_token(payload),
        scope=spotify.get("scope") or "",
    )
    return access


class SpotifyStatus(BaseModel):
    configured: bool
    connected: bool
    premium_required: bool = True
    message: str


class PlayerToken(BaseModel):
    access_token: str


@router.get("/status", response_model=SpotifyStatus)
async def status(gt_sid: str | None = Cookie(default=None)):
    if not configured():
        return SpotifyStatus(
            configured=False,
            connected=False,
            message="Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in API .env",
        )
    token = await _valid_access_token(gt_sid or "")
    return SpotifyStatus(
        configured=True,
        connected=bool(token),
        message="Connected — full playback via Spotify Premium."
        if token
        else "Connect Spotify for full-length tracks.",
    )


@router.get("/login")
async def login(gt_sid: str | None = Cookie(default=None)):
    if not configured():
        raise HTTPException(status_code=503, detail="Spotify integration not configured")
    session_id = gt_sid or str(uuid4())
    state = secrets.token_urlsafe(16)
    response = RedirectResponse(authorize_url(state=state), status_code=302)
    response.set_cookie("gt_sid", session_id, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 90)
    response.set_cookie("spotify_oauth_state", state, httponly=True, samesite="lax", max_age=600)
    return response


@router.get("/callback")
async def callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    gt_sid: str | None = Cookie(default=None),
    spotify_oauth_state: str | None = Cookie(default=None),
):
    if error:
        return RedirectResponse(f"{_frontend_redirect()}?spotify=error")
    if not code or not state or state != spotify_oauth_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    db = get_catalog_db()
    if db is None:
        raise HTTPException(status_code=503, detail="MongoDB unavailable")
    session_id = gt_sid or str(uuid4())
    payload = await exchange_code(code)
    await upsert_spotify_tokens(
        db,
        session_id,
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token"),
        expires_at=expires_at_from_token(payload),
        scope=payload.get("scope") or "",
    )
    resp = RedirectResponse(f"{_frontend_redirect()}?spotify=connected", status_code=302)
    resp.set_cookie("gt_sid", session_id, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 90)
    resp.delete_cookie("spotify_oauth_state")
    return resp


@router.get("/token", response_model=PlayerToken)
async def player_token(gt_sid: str | None = Cookie(default=None)):
    if not configured():
        raise HTTPException(status_code=503, detail="Spotify not configured")
    access = await _valid_access_token(gt_sid or "")
    if not access:
        raise HTTPException(status_code=401, detail="Spotify not connected")
    return PlayerToken(access_token=access)


class MatchResult(BaseModel):
    matched: int
    total: int
    missing: int


@router.post("/match-liked", response_model=MatchResult)
async def match_liked(gt_sid: str | None = Cookie(default=None)):
    """Map Liked Music targets to Spotify track URIs (full catalog)."""
    access = await _valid_access_token(gt_sid or "")
    if not access:
        raise HTTPException(status_code=401, detail="Connect Spotify first")
    db = get_catalog_db()
    if db is None:
        raise HTTPException(status_code=503, detail="MongoDB unavailable")

    matched = 0
    for target in LIKED_MUSIC_ALL:
        doc = await db.tracks.find_one(
            {
                "discovery.liked_music_target.title": target.title,
                "discovery.liked_music_target.artist": target.artist,
            }
        )
        if not doc:
            continue
        hit = await search_track(access, title=target.title, artist=target.artist)
        if not hit:
            continue
        uri = hit.get("uri")
        if not uri:
            continue
        await db.tracks.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "playback.spotify_uri": uri,
                    "playback.spotify_id": hit.get("id"),
                    "playback.preview_only": False,
                    "identifiers.isrc": hit.get("external_ids", {}).get("isrc")
                    or (doc.get("identifiers") or {}).get("isrc"),
                }
            },
        )
        matched += 1

    return MatchResult(matched=matched, total=len(LIKED_MUSIC_ALL), missing=len(LIKED_MUSIC_ALL) - matched)


@router.get("/track-uri")
async def track_uri(
    title: str = Query(..., min_length=1),
    artist: str = Query(..., min_length=1),
    gt_sid: str | None = Cookie(default=None),
):
    access = await _valid_access_token(gt_sid or "")
    if not access:
        raise HTTPException(status_code=401, detail="Connect Spotify first")
    hit = await search_track(access, title=title, artist=artist)
    if not hit:
        raise HTTPException(status_code=404, detail="No Spotify match")
    return {"uri": hit.get("uri"), "id": hit.get("id"), "name": hit.get("name")}
