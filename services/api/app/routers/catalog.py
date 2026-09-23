from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.catalog_seed import SEED_TRACKS, ensure_demo_audio, track_by_id
from app.db.session import try_db
from app.models.db import Album, Artist, Track, TrackProvider

router = APIRouter(tags=["catalog"])


class TrackOut(BaseModel):
    id: str
    title: str
    artist: str = ""
    album: Optional[str] = None
    duration_ms: int
    artwork_url: Optional[str] = None
    isrc: Optional[str] = None
    genres: Optional[list[str]] = None
    providers: list[str] = []

    class Config:
        from_attributes = True


class HomeItem(BaseModel):
    id: str
    title: str
    artist: str
    album: Optional[str] = None
    duration_ms: int


class HomeSection(BaseModel):
    id: str
    title: str
    items: list[HomeItem]


class HomeResponse(BaseModel):
    sections: list[HomeSection]
    source: str


class SearchResponse(BaseModel):
    tracks: list[TrackOut]
    artists: list[dict]
    albums: list[dict]


class StreamResponse(BaseModel):
    track_id: str
    provider: str
    playback_type: str
    url: Optional[str] = None
    message: str


def _seed_track_out(t) -> TrackOut:
    return TrackOut(
        id=t.id,
        title=t.title,
        artist=t.artist,
        album=t.album,
        duration_ms=t.duration_ms,
        genres=t.genres,
        providers=[t.provider],
    )


def _absolute(request: Request, path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    base = str(request.base_url).rstrip("/")
    return f"{base}{path if path.startswith('/') else '/' + path}"


@router.get("/home", response_model=HomeResponse)
async def home_feed():
    ensure_demo_audio()
    items = [
        HomeItem(
            id=t.id,
            title=t.title,
            artist=t.artist,
            album=t.album,
            duration_ms=t.duration_ms,
        )
        for t in SEED_TRACKS
    ]
    return HomeResponse(
        sections=[
            HomeSection(id="quick_picks", title="Quick picks", items=items),
            HomeSection(
                id="listen_again",
                title="Listen again",
                items=list(reversed(items)),
            ),
            HomeSection(id="made_for_you", title="Made for you", items=items[:3]),
        ],
        source="seed-open-audio",
    )


@router.get("/search", response_model=SearchResponse)
async def search(q: str = Query(min_length=1), limit: int = Query(default=20, le=50)):
    ensure_demo_audio()
    q_lower = q.lower()
    seed_hits = [
        _seed_track_out(t)
        for t in SEED_TRACKS
        if q_lower in t.title.lower()
        or q_lower in t.artist.lower()
        or q_lower in t.album.lower()
    ][:limit]

    db = await try_db()
    if db is not None:
        try:
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
                await db.scalars(
                    select(Artist).where(Artist.name.ilike(pattern)).limit(limit)
                )
            ).all()
            albums = (
                await db.scalars(
                    select(Album).where(Album.title.ilike(pattern)).limit(limit)
                )
            ).all()
            if tracks or artists or albums:
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
                    ]
                    or seed_hits,
                    artists=[
                        {"id": a.id, "name": a.name, "image_url": a.image_url}
                        for a in artists
                    ],
                    albums=[
                        {"id": a.id, "title": a.title, "artwork_url": a.artwork_url}
                        for a in albums
                    ],
                )
        except Exception:
            pass
        finally:
            await db.close()

    artists = sorted({t.artist for t in SEED_TRACKS if q_lower in t.artist.lower()})
    albums = sorted({t.album for t in SEED_TRACKS if q_lower in t.album.lower()})
    return SearchResponse(
        tracks=seed_hits,
        artists=[{"id": a, "name": a, "image_url": None} for a in artists],
        albums=[{"id": a, "title": a, "artwork_url": None} for a in albums],
    )


@router.get("/tracks/{track_id}", response_model=TrackOut)
async def get_track(track_id: str):
    seed = track_by_id(track_id)
    if seed:
        return _seed_track_out(seed)

    db = await try_db()
    if db is not None:
        try:
            track = await db.scalar(
                select(Track)
                .options(selectinload(Track.providers))
                .where(Track.id == track_id)
            )
            if track:
                return TrackOut(
                    id=track.id,
                    title=track.title,
                    duration_ms=track.duration_ms,
                    artwork_url=track.artwork_url,
                    isrc=track.isrc,
                    genres=track.genres,
                    providers=[p.provider for p in track.providers],
                )
        except Exception:
            pass
        finally:
            await db.close()

    raise HTTPException(status_code=404, detail="Track not found")


@router.get("/tracks/{track_id}/stream", response_model=StreamResponse)
async def resolve_stream(track_id: str, request: Request):
    """Resolve playback via provider map / open seed audio — never scrapes commercial streams."""
    ensure_demo_audio()
    seed = track_by_id(track_id)
    if seed:
        return StreamResponse(
            track_id=track_id,
            provider=seed.provider,
            playback_type="stream",
            url=_absolute(request, seed.stream_path),
            message="Resolved via open/demo provider adapter",
        )

    db = await try_db()
    if db is not None:
        try:
            providers = (
                await db.scalars(
                    select(TrackProvider).where(
                        TrackProvider.track_id == track_id,
                        TrackProvider.availability == "available",
                    )
                )
            ).all()
            if providers:
                priority = {"user_owned": 0, "open": 1}
                chosen = sorted(providers, key=lambda p: priority.get(p.provider, 50))[0]
                return StreamResponse(
                    track_id=track_id,
                    provider=chosen.provider,
                    playback_type=chosen.playback_type,
                    url=_absolute(request, chosen.stream_url),
                    message="Resolved via provider adapter",
                )
        except Exception:
            pass
        finally:
            await db.close()

    raise HTTPException(
        status_code=404,
        detail="No playable provider mapped for this track",
    )
