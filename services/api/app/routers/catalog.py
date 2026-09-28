from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel

from app.catalog.liked_music_seed import PLAYLIST_DESCRIPTION as LIKED_DESC
from app.catalog.liked_music_seed import PLAYLIST_ID as LIKED_SLUG
from app.catalog.liked_music_seed import PLAYLIST_TITLE as LIKED_TITLE
from app.catalog.playback_resolve import resolve_playback_stream
from app.catalog.service import CatalogService, mongo_track_to_track_out, seed_track_to_track_out
from app.catalog_seed import ensure_demo_audio, track_by_id as seed_track_by_id
from app.database.client import get_catalog_db
from app.database.repositories.albums import AlbumRepository
from app.database.repositories.artists import ArtistRepository
from app.database.repositories.tracks import TrackRepository, track_id_str

router = APIRouter(tags=["catalog"])
catalog = CatalogService()


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
    playable: bool = True
    preview_only: bool = False
    spotify_uri: Optional[str] = None


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


class GenreOut(BaseModel):
    slug: str
    name: str
    track_count: int


class GenreListResponse(BaseModel):
    genres: list[GenreOut]
    source: str


class GenreTracksResponse(BaseModel):
    slug: str
    name: str
    tracks: list[TrackOut]
    source: str


class SearchResponse(BaseModel):
    tracks: list[TrackOut]
    artists: list[dict]
    albums: list[dict]
    genres: list[dict] = []
    source: str


class StreamResponse(BaseModel):
    track_id: str
    provider: str
    playback_type: str
    url: Optional[str] = None
    message: str


def _track_out(data: dict) -> TrackOut:
    return TrackOut(
        id=data["id"],
        title=data["title"],
        artist=data.get("artist") or "",
        album=data.get("album"),
        duration_ms=data["duration_ms"],
        artwork_url=data.get("artwork_url"),
        isrc=data.get("isrc"),
        genres=data.get("genres"),
        providers=data.get("providers") or [],
        playable=bool(data.get("playable", True)),
        preview_only=bool(data.get("preview_only", False)),
        spotify_uri=data.get("spotify_uri"),
    )


@router.get("/genres", response_model=GenreListResponse)
async def list_genres():
    ensure_demo_audio()
    genres = await catalog.list_genres()
    return GenreListResponse(
        genres=[GenreOut(**g) for g in genres],
        source=catalog.source,
    )


@router.get("/genres/{slug}/tracks", response_model=GenreTracksResponse)
async def genre_tracks(slug: str):
    ensure_demo_audio()
    genres = await catalog.list_genres()
    name = next((g["name"] for g in genres if g["slug"] == slug.lower()), slug.replace("-", " ").title())
    tracks = await catalog.genre_tracks(slug.lower(), public_only=True)
    return GenreTracksResponse(
        slug=slug.lower(),
        name=name,
        tracks=[_track_out(t) for t in tracks if t.get("playable", True)],
        source=catalog.source,
    )


class PlaylistOut(BaseModel):
    id: str
    title: str
    description: str
    track_count: int
    tracks: list[TrackOut]


async def _playlist_from_mongo(
    request: Request,
    *,
    slug: str,
    title: str,
    description: str,
) -> PlaylistOut | None:
    db = get_catalog_db()
    if db is None:
        return None
    doc = await db.playlists.find_one({"slug": slug})
    if not doc:
        return None
    repo = TrackRepository(db)
    tracks: list[TrackOut] = []
    for tid in doc.get("track_ids") or []:
        hit = await repo.get_by_id(str(tid))
        if not hit or not (hit.get("playback") or {}).get("available"):
            continue
        tracks.append(_track_out(mongo_track_to_track_out(hit, request)))
    part_note = ""
    parts = doc.get("parts") or {}
    if parts:
        part_note = f" ({len(parts)} part{'s' if len(parts) != 1 else ''} imported)"
    return PlaylistOut(
        id=slug,
        title=(doc.get("title") or title) + part_note,
        description=doc.get("description") or description,
        track_count=len(tracks),
        tracks=tracks,
    )


@router.get("/playlists/liked-music", response_model=PlaylistOut)
async def playlist_liked_music(request: Request):
    ensure_demo_audio()
    out = await _playlist_from_mongo(
        request,
        slug=LIKED_SLUG,
        title=LIKED_TITLE,
        description=LIKED_DESC,
    )
    if out:
        return out
    raise HTTPException(
        status_code=404,
        detail="Liked Music playlist not imported yet. Run: python scripts/import_liked_music.py",
    )


@router.get("/playlists/major-afrobeats", response_model=PlaylistOut)
async def playlist_major_afrobeats(request: Request):
    """Curated star Afrobeats playlist (featured artist catalog)."""
    ensure_demo_audio()
    db = get_catalog_db()
    if db is None:
        rows = await catalog.genre_tracks("afrobeats", public_only=True)
        tracks = [_track_out(r) for r in rows[:40] if r.get("playable", True)]
        return PlaylistOut(
            id="major-afrobeats",
            title="Major Afrobeats",
            description="Davido, Burna Boy, Wizkid, Asake, Rema, Odumodublvck, and more.",
            track_count=len(tracks),
            tracks=tracks,
        )
    repo = TrackRepository(db)
    docs = await repo.featured_tracks(limit=80, genre="afrobeats")
    tracks = [_track_out(mongo_track_to_track_out(d, request)) for d in docs]
    return PlaylistOut(
        id="major-afrobeats",
        title="Major Afrobeats",
        description="Star artists — playable from your GreenTube catalog.",
        track_count=len(tracks),
        tracks=tracks,
    )


@router.get("/tracks", response_model=list[TrackOut])
async def list_tracks(
    request: Request,
    limit: int = Query(default=50, le=200),
    skip: int = Query(default=0, ge=0),
    genre: Optional[str] = None,
    playable_only: bool = Query(default=True),
):
    ensure_demo_audio()
    rows = await catalog.list_tracks(
        limit=limit,
        skip=skip,
        playable_only=playable_only,
        genre=genre,
        request=request,
    )
    out = [_track_out(r) for r in rows]
    if playable_only:
        out = [t for t in out if t.playable]
    return out


@router.get("/trending", response_model=list[TrackOut])
async def trending(request: Request, limit: int = Query(default=20, le=100)):
    ensure_demo_audio()
    db = get_catalog_db()
    if db is not None:
        repo = TrackRepository(db)
        docs = await repo.trending(limit=limit)
        if docs:
            return [
                _track_out(mongo_track_to_track_out(d, request))
                for d in docs
                if (d.get("playback") or {}).get("available")
            ]
    rows = await catalog.list_tracks(limit=limit, request=request)
    return [_track_out(r) for r in rows if r.get("playable", True)]


@router.get("/new-releases", response_model=list[TrackOut])
async def new_releases(request: Request, limit: int = Query(default=20, le=100)):
    ensure_demo_audio()
    db = get_catalog_db()
    if db is not None:
        repo = TrackRepository(db)
        docs = await repo.new_releases(limit=limit)
        if docs:
            return [
                _track_out(mongo_track_to_track_out(d, request))
                for d in docs
                if (d.get("playback") or {}).get("available")
            ]
    rows = await catalog.list_tracks(limit=limit, request=request)
    return [_track_out(r) for r in rows if r.get("playable", True)]


@router.get("/home", response_model=HomeResponse)
async def home_feed(request: Request):
    ensure_demo_audio()
    db = get_catalog_db()
    if db is not None:
        repo = TrackRepository(db)
        featured_docs = await repo.featured_tracks(limit=24)
        if len(featured_docs) >= 8:
            rows = [mongo_track_to_track_out(d, request) for d in featured_docs]
        else:
            trending = await repo.trending(limit=24)
            rows = [mongo_track_to_track_out(d, request) for d in featured_docs + trending][:24]
    else:
        rows = await catalog.list_tracks(limit=24, playable_only=True, request=request)
    items = [
        HomeItem(
            id=r["id"],
            title=r["title"],
            artist=r["artist"],
            album=r.get("album"),
            duration_ms=r["duration_ms"],
        )
        for r in rows
        if r.get("playable", True)
    ]

    genre_sections: list[HomeSection] = []
    for slug, title in [
        ("afrobeats", "Afrobeats essentials"),
        ("hip-hop", "Hip-Hop flow"),
        ("jazz", "Jazz & blues"),
        ("electronic", "Electronic energy"),
        ("chill", "Chill & unwind"),
    ]:
        genre_rows = await catalog.genre_tracks(slug, public_only=True)
        playable = [r for r in genre_rows if r.get("playable", True)][:12]
        if playable:
            genre_sections.append(
                HomeSection(
                    id=f"genre_{slug}",
                    title=title,
                    items=[
                        HomeItem(
                            id=r["id"],
                            title=r["title"],
                            artist=r["artist"],
                            album=r.get("album"),
                            duration_ms=r["duration_ms"],
                        )
                        for r in playable
                    ],
                )
            )

    featured_items: list[HomeItem] = []
    if db is not None:
        featured_docs = await TrackRepository(db).featured_tracks(limit=16, genre="afrobeats")
        featured_items = [
            HomeItem(
                id=track_id_str(d),
                title=d.get("title") or "",
                artist=(d.get("artist") or {}).get("name") or "",
                album=(d.get("album") or {}).get("title"),
                duration_ms=int((d.get("duration_seconds") or 0) * 1000),
            )
            for d in featured_docs
        ]

    return HomeResponse(
        sections=[
            *(
                [
                    HomeSection(
                        id="featured_stars",
                        title="Major artists — Afrobeats",
                        items=featured_items,
                    )
                ]
                if featured_items
                else []
            ),
            HomeSection(id="quick_picks", title="Quick picks", items=items),
            *genre_sections,
            HomeSection(id="listen_again", title="Listen again", items=list(reversed(items))),
            HomeSection(id="made_for_you", title="Made for you", items=items[:4]),
        ],
        source=catalog.source,
    )


@router.get("/search", response_model=SearchResponse)
async def search(q: str = Query(min_length=1), limit: int = Query(default=20, le=50)):
    ensure_demo_audio()
    result = await catalog.search(q, limit=limit)
    tracks = [_track_out(t) for t in result["tracks"] if t.get("playable", True)]
    return SearchResponse(
        tracks=tracks,
        artists=result["artists"],
        albums=result["albums"],
        genres=result.get("genres") or [],
        source=catalog.source,
    )


@router.get("/artists")
async def list_artists(limit: int = Query(default=50, le=200), skip: int = Query(default=0, ge=0)):
    db = get_catalog_db()
    if db is not None:
        repo = ArtistRepository(db)
        rows = await repo.list_artists(limit=limit, skip=skip)
        return {
            "artists": [
                {
                    "id": str(a["_id"]),
                    "name": a.get("name"),
                    "image_url": a.get("image_url"),
                    "genres": a.get("genres") or [],
                }
                for a in rows
            ],
            "source": "mongodb",
        }
    from app.catalog_seed import SEED_TRACKS

    names = sorted({t.artist for t in SEED_TRACKS})
    return {
        "artists": [{"id": n, "name": n, "image_url": None, "genres": []} for n in names[skip : skip + limit]],
        "source": "seed-open-audio",
    }


@router.get("/artists/{artist_id}")
async def get_artist(artist_id: str):
    db = get_catalog_db()
    if db is not None:
        repo = ArtistRepository(db)
        doc = await repo.get_by_id(artist_id)
        if doc:
            return {
                "id": str(doc["_id"]),
                "name": doc.get("name"),
                "bio": doc.get("bio"),
                "image_url": doc.get("image_url"),
                "genres": doc.get("genres") or [],
                "country": doc.get("country"),
                "musicbrainz_id": doc.get("musicbrainz_id"),
                "source": "mongodb",
            }
    raise HTTPException(status_code=404, detail="Artist not found")


@router.get("/albums")
async def list_albums(limit: int = Query(default=50, le=200), skip: int = Query(default=0, ge=0)):
    db = get_catalog_db()
    if db is not None:
        repo = AlbumRepository(db)
        rows = await repo.list_albums(limit=limit, skip=skip)
        return {
            "albums": [
                {
                    "id": str(a["_id"]),
                    "title": a.get("title"),
                    "artist_id": str(a.get("artist_id")) if a.get("artist_id") else None,
                    "artwork_url": a.get("artwork_url"),
                    "release_date": a.get("release_date"),
                    "genres": a.get("genres") or [],
                }
                for a in rows
            ],
            "source": "mongodb",
        }
    from app.catalog_seed import SEED_TRACKS

    albums = sorted({t.album for t in SEED_TRACKS})
    return {
        "albums": [
            {"id": a, "title": a, "artist_id": None, "artwork_url": None, "release_date": None, "genres": []}
            for a in albums[skip : skip + limit]
        ],
        "source": "seed-open-audio",
    }


@router.get("/albums/{album_id}")
async def get_album(album_id: str):
    db = get_catalog_db()
    if db is not None:
        repo = AlbumRepository(db)
        doc = await repo.get_by_id(album_id)
        if doc:
            return {
                "id": str(doc["_id"]),
                "title": doc.get("title"),
                "artist_id": str(doc.get("artist_id")) if doc.get("artist_id") else None,
                "artwork_url": doc.get("artwork_url"),
                "release_date": doc.get("release_date"),
                "genres": doc.get("genres") or [],
                "track_count": doc.get("track_count") or 0,
                "source": "mongodb",
            }
    raise HTTPException(status_code=404, detail="Album not found")


@router.get("/tracks/{track_id}", response_model=TrackOut)
async def get_track(track_id: str, request: Request):
    ensure_demo_audio()
    row = await catalog.get_track(track_id, request)
    if not row:
        raise HTTPException(status_code=404, detail="Track not found")
    return _track_out(row)


def _is_remote_url(url: str) -> bool:
    try:
        return urlparse(url).scheme in ("http", "https")
    except Exception:
        return False


async def _proxy_audio(url: str) -> StreamingResponse:
    """Stream remote MP3 through the API so <audio> stays same-origin (no CORS on Deezer/Audius)."""
    client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=120.0), follow_redirects=True)
    try:
        req = client.build_request("GET", url)
        upstream = await client.send(req, stream=True)
        upstream.raise_for_status()
    except Exception as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Upstream audio failed: {exc}") from exc

    media_type = upstream.headers.get("content-type") or "audio/mpeg"

    async def body():
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(body(), media_type=media_type)


async def _resolve_playback_url(track_id: str, request: Request) -> str | None:
    from app.config import get_settings

    settings = get_settings()
    db = get_catalog_db()
    if db is not None:
        doc = await TrackRepository(db).get_by_id(track_id)
        playback = (doc or {}).get("playback") or {}
        if doc and playback.get("spotify_uri") and not playback.get("available"):
            return None
        if doc and playback.get("preview_only") and not settings.allow_preview_playback:
            return None
        if doc and (doc.get("source") or {}).get("provider") == "deezer" and not settings.allow_preview_playback:
            return None
        if doc and playback.get("available"):
            url = await resolve_playback_stream(doc)
            if url:
                patch: dict = {
                    "playback.stream_url": url,
                    "playback.resolved_via": "playback_resolve",
                }
                if "dzcdn.net" in url or "deezer" in url:
                    patch["playback.preview_only"] = True
                else:
                    patch["playback.preview_only"] = False
                await db.tracks.update_one({"_id": doc["_id"]}, {"$set": patch})
                return url
    row = await catalog.get_track(track_id, request)
    if row and row.get("playable") and row.get("stream_url"):
        return row["stream_url"]
    return None


@router.get("/tracks/{track_id}/audio")
async def stream_audio_redirect(track_id: str, request: Request):
    """Same-origin URL for <audio src> — proxies remote streams, redirects local static."""
    ensure_demo_audio()
    url = await _resolve_playback_url(track_id, request)
    if url:
        if _is_remote_url(url):
            return await _proxy_audio(url)
        from app.catalog.service import _absolute

        return RedirectResponse(url=_absolute(request, url), status_code=302)
    seed = seed_track_by_id(track_id)
    if seed:
        from app.catalog.service import _absolute

        return RedirectResponse(url=_absolute(request, seed.stream_path), status_code=302)
    raise HTTPException(status_code=404, detail="No playable stream for this track")


@router.get("/tracks/{track_id}/stream", response_model=StreamResponse)
async def resolve_stream(track_id: str, request: Request):
    ensure_demo_audio()
    row = await catalog.get_track(track_id, request)
    if row and row.get("playable") and row.get("stream_url"):
        provider = (row.get("providers") or ["local"])[0]
        return StreamResponse(
            track_id=track_id,
            provider=provider,
            playback_type="stream",
            url=row["stream_url"],
            message="Resolved via catalog playback adapter",
        )

    seed = seed_track_by_id(track_id)
    if seed:
        from app.catalog.service import _absolute

        return StreamResponse(
            track_id=track_id,
            provider=seed.provider,
            playback_type="stream",
            url=_absolute(request, seed.stream_path),
            message="Resolved via open/demo provider adapter",
        )

    raise HTTPException(
        status_code=404,
        detail="No playable provider mapped for this track",
    )
