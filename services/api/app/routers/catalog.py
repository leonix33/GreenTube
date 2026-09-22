from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.db import Album, Artist, Track, TrackProvider

router = APIRouter(tags=["catalog"])


class TrackOut(BaseModel):
    id: str
    title: str
    duration_ms: int
    artwork_url: Optional[str] = None
    isrc: Optional[str] = None
    genres: Optional[list[str]] = None
    providers: list[str] = []

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    tracks: list[TrackOut]
    artists: list[dict]
    albums: list[dict]


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, le=50),
    db: AsyncSession = Depends(get_db),
):
    pattern = f"%{q}%"
    tracks = (
        await db.scalars(
            select(Track)
            .options(selectinload(Track.providers))
            .where(Track.title.ilike(pattern))
            .limit(limit)
        )
    ).all()
    artists = (
        await db.scalars(select(Artist).where(Artist.name.ilike(pattern)).limit(limit))
    ).all()
    albums = (
        await db.scalars(select(Album).where(Album.title.ilike(pattern)).limit(limit))
    ).all()

    return SearchResponse(
        tracks=[
            TrackOut(
                id=t.id,
                title=t.title,
                duration_ms=t.duration_ms,
                artwork_url=t.artwork_url,
                isrc=t.isrc,
                genres=t.genres,
                providers=[p.provider for p in t.providers],
            )
            for t in tracks
        ],
        artists=[{"id": a.id, "name": a.name, "image_url": a.image_url} for a in artists],
        albums=[
            {"id": a.id, "title": a.title, "artwork_url": a.artwork_url} for a in albums
        ],
    )


@router.get("/tracks/{track_id}", response_model=TrackOut)
async def get_track(track_id: str, db: AsyncSession = Depends(get_db)):
    track = await db.scalar(
        select(Track).options(selectinload(Track.providers)).where(Track.id == track_id)
    )
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return TrackOut(
        id=track.id,
        title=track.title,
        duration_ms=track.duration_ms,
        artwork_url=track.artwork_url,
        isrc=track.isrc,
        genres=track.genres,
        providers=[p.provider for p in track.providers],
    )


class StreamResponse(BaseModel):
    track_id: str
    provider: str
    playback_type: str
    url: Optional[str] = None
    message: str


@router.get("/tracks/{track_id}/stream", response_model=StreamResponse)
async def resolve_stream(track_id: str, db: AsyncSession = Depends(get_db)):
    """Resolve playback via TrackProvider — never assumes a scraped source."""
    providers = (
        await db.scalars(
            select(TrackProvider).where(
                TrackProvider.track_id == track_id,
                TrackProvider.availability == "available",
            )
        )
    ).all()
    if not providers:
        raise HTTPException(
            status_code=404,
            detail="No playable provider mapped for this track",
        )
    # Prefer user_owned, then open, then licensed
    priority = {"user_owned": 0, "open": 1}
    chosen = sorted(providers, key=lambda p: priority.get(p.provider, 50))[0]
    return StreamResponse(
        track_id=track_id,
        provider=chosen.provider,
        playback_type=chosen.playback_type,
        url=chosen.stream_url,
        message="Resolved via provider adapter",
    )


@router.get("/home")
async def home_feed():
    """Placeholder personalized home — recommendation service will fill this."""
    return {
        "greeting_sections": [
            {"id": "quick_picks", "title": "Quick picks", "items": []},
            {"id": "listen_again", "title": "Listen again", "items": []},
            {"id": "made_for_you", "title": "Made for you", "items": []},
        ],
        "source": "stub",
    }
