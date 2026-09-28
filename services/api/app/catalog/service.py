from __future__ import annotations

from typing import Any, Optional

from fastapi import Request

from app.catalog_seed import (
    GENRES as SEED_GENRES,
    SEED_TRACKS,
    ensure_demo_audio,
    track_by_id as seed_track_by_id,
    tracks_for_genre as seed_tracks_for_genre,
)
from app.config import get_settings
from app.database.client import get_catalog_db, is_mongodb_connected
from app.database.repositories.genres import GenreRepository
from app.database.repositories.search import CatalogSearchRepository
from app.database.repositories.tracks import TrackRepository, track_id_str


def _absolute(request: Request | None, path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if request is None:
        return path
    base = str(request.base_url).rstrip("/")
    return f"{base}{path if path.startswith('/') else '/' + path}"


def mongo_track_to_track_out(doc: dict[str, Any], request: Request | None = None) -> dict[str, Any]:
    playback = doc.get("playback") or {}
    source = doc.get("source") or {}
    artist = doc.get("artist") or {}
    album = doc.get("album") or {}
    stream_path = playback.get("stream_url")
    providers = []
    if playback.get("available"):
        providers.append(source.get("provider") or "local")

    settings = get_settings()
    provider = source.get("provider") or ""
    preview_only = bool(playback.get("preview_only") or provider == "deezer")
    previews_allowed = settings.allow_preview_playback
    has_spotify = bool(playback.get("spotify_uri"))
    has_full_stream = bool(
        playback.get("available")
        and not preview_only
        and (previews_allowed or provider != "deezer")
    )
    has_preview_stream = bool(
        playback.get("available") and preview_only and previews_allowed
    )

    duration_ms = int((doc.get("duration_seconds") or 0) * 1000)
    if preview_only and not has_spotify:
        duration_ms = min(duration_ms, 30_000) if duration_ms else 30_000

    return {
        "id": track_id_str(doc),
        "title": doc.get("title") or "",
        "artist": artist.get("name") or "",
        "album": album.get("title"),
        "duration_ms": duration_ms,
        "artwork_url": doc.get("artwork_url"),
        "isrc": (doc.get("identifiers") or {}).get("isrc"),
        "genres": doc.get("genres") or [],
        "providers": providers,
        "playable": bool(has_spotify or has_full_stream or has_preview_stream),
        "preview_only": preview_only and not has_spotify,
        "spotify_uri": playback.get("spotify_uri"),
        "stream_url": _absolute(request, stream_path)
        if (has_full_stream or has_preview_stream)
        else None,
    }


def seed_track_to_track_out(t, request: Request | None = None) -> dict[str, Any]:
    ensure_demo_audio()
    return {
        "id": t.id,
        "title": t.title,
        "artist": t.artist,
        "album": t.album,
        "duration_ms": t.duration_ms,
        "artwork_url": None,
        "isrc": None,
        "genres": t.genres,
        "providers": [t.provider],
        "playable": True,
        "stream_url": _absolute(request, t.stream_path),
    }


class CatalogService:
    """MongoDB-first catalog with seed fallback when Atlas is unavailable."""

    @property
    def _db(self):
        return get_catalog_db()

    @property
    def _tracks(self) -> TrackRepository | None:
        db = self._db
        return TrackRepository(db) if db is not None else None

    @property
    def _genres(self) -> GenreRepository | None:
        db = self._db
        return GenreRepository(db) if db is not None else None

    @property
    def _search(self) -> CatalogSearchRepository | None:
        db = self._db
        return CatalogSearchRepository(db) if db is not None else None

    @property
    def source(self) -> str:
        return "mongodb" if is_mongodb_connected() else "seed-open-audio"

    async def list_genres(self) -> list[dict[str, Any]]:
        if self._genres is not None:
            await self._genres.sync_taxonomy_from_seed()
            await self._genres.refresh_track_counts()
            rows = await self._genres.list_genres()
            return [
                {
                    "slug": r["slug"],
                    "name": r["name"],
                    "track_count": int(r.get("track_count") or 0),
                }
                for r in rows
            ]
        from app.catalog_seed import genre_track_counts

        counts = genre_track_counts()
        return [
            {"slug": g.slug, "name": g.name, "track_count": counts.get(g.slug, 0)}
            for g in SEED_GENRES
        ]

    async def genre_tracks(self, slug: str, *, public_only: bool = True) -> list[dict[str, Any]]:
        if self._tracks is not None:
            docs = await self._tracks.tracks_by_genre(slug, playable_only=public_only)
            if docs:
                return [mongo_track_to_track_out(d) for d in docs]
            if public_only:
                docs = await self._tracks.tracks_by_genre(slug, playable_only=False)
                if docs:
                    return [mongo_track_to_track_out(d) for d in docs if (d.get("playback") or {}).get("available")]
        return [seed_track_to_track_out(t) for t in seed_tracks_for_genre(slug)]

    async def get_track(self, track_id: str, request: Request | None = None) -> Optional[dict[str, Any]]:
        if self._tracks is not None:
            doc = await self._tracks.get_by_id(track_id)
            if doc:
                return mongo_track_to_track_out(doc, request)
        seed = seed_track_by_id(track_id)
        if seed:
            return seed_track_to_track_out(seed, request)
        return None

    async def list_tracks(
        self,
        *,
        limit: int = 50,
        skip: int = 0,
        playable_only: bool = True,
        genre: str | None = None,
        request: Request | None = None,
    ) -> list[dict[str, Any]]:
        if self._tracks is not None:
            docs = await self._tracks.list_tracks(
                limit=limit, skip=skip, playable_only=playable_only, genre=genre
            )
            if docs:
                return [mongo_track_to_track_out(d, request) for d in docs]
        items = SEED_TRACKS if not genre else seed_tracks_for_genre(genre)
        return [seed_track_to_track_out(t, request) for t in items[skip : skip + limit]]

    async def search(self, q: str, *, limit: int = 20) -> dict[str, Any]:
        if self._search is not None:
            result = await self._search.search(q, limit=limit, playable_only_for_tracks=False)
            return {
                "tracks": [mongo_track_to_track_out(t) for t in result["tracks"]],
                "artists": [
                    {
                        "id": str(a["_id"]),
                        "name": a.get("name"),
                        "image_url": a.get("image_url"),
                    }
                    for a in result["artists"]
                ],
                "albums": [
                    {
                        "id": str(a["_id"]),
                        "title": a.get("title"),
                        "artwork_url": a.get("artwork_url"),
                    }
                    for a in result["albums"]
                ],
                "genres": [
                    {"slug": g.get("slug"), "name": g.get("name")} for g in result["genres"]
                ],
            }

        q_lower = q.lower()
        tracks = [
            seed_track_to_track_out(t)
            for t in SEED_TRACKS
            if q_lower in t.title.lower()
            or q_lower in t.artist.lower()
            or q_lower in t.album.lower()
            or any(q_lower in g for g in t.genres)
        ][:limit]
        artists = sorted({t.artist for t in SEED_TRACKS if q_lower in t.artist.lower()})
        albums = sorted({t.album for t in SEED_TRACKS if q_lower in t.album.lower()})
        genres = [
            {"slug": g.slug, "name": g.name}
            for g in SEED_GENRES
            if q_lower in g.slug or q_lower in g.name.lower()
        ]
        return {
            "tracks": tracks,
            "artists": [{"id": a, "name": a, "image_url": None} for a in artists],
            "albums": [{"id": a, "title": a, "artwork_url": None} for a in albums],
            "genres": genres,
        }

    async def stats(self) -> dict[str, Any]:
        if self._tracks is None:
            return {
                "total_tracks": len(SEED_TRACKS),
                "playable_tracks": len(SEED_TRACKS),
                "metadata_only_tracks": 0,
                "artists": len({t.artist for t in SEED_TRACKS}),
                "albums": len({t.album for t in SEED_TRACKS}),
                "genres": len(SEED_GENRES),
                "tracks_by_provider": {"local": len(SEED_TRACKS)},
                "source": "seed-open-audio",
            }
        total = await self._tracks.count(playable_only=False)
        playable = await self._tracks.count(playable_only=True)
        metadata_only = total - playable
        by_provider = await self._tracks.count_by_provider()
        artists = await self._db.artists.count_documents({})
        albums = await self._db.albums.count_documents({})
        genres = await self._genres.count() if self._genres else 0
        return {
            "total_tracks": total,
            "playable_tracks": playable,
            "metadata_only_tracks": metadata_only,
            "artists": artists,
            "albums": albums,
            "genres": genres,
            "tracks_by_provider": by_provider,
            "source": "mongodb",
        }
