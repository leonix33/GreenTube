from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase


async def _drop_index_if_exists(collection, name: str) -> None:
    try:
        await collection.drop_index(name)
    except Exception:
        pass


async def ensure_catalog_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create indexes for catalog queries, dedupe, and future Atlas Search migration."""
    artists = db.artists
    await artists.update_many({"musicbrainz_id": None}, {"$unset": {"musicbrainz_id": ""}})

    tracks = db.tracks
    await tracks.create_index("title")
    await tracks.create_index("slug")
    await tracks.create_index("artist.name")
    await tracks.create_index("album.title")
    await tracks.create_index("genres")
    await tracks.create_index("identifiers.isrc", sparse=True)
    await tracks.create_index("identifiers.musicbrainz_recording_id", sparse=True)
    await tracks.create_index([("source.provider", 1), ("source.provider_track_id", 1)], unique=True)
    await tracks.create_index("release_date")
    await tracks.create_index("discovery.trending_score")
    await tracks.create_index("playback.available")
    await tracks.create_index(
        [
            ("artist.name", "text"),
            ("title", "text"),
            ("album.title", "text"),
            ("genres", "text"),
        ],
        name="catalog_text_search",
    )

    await db.playlists.create_index("slug", unique=True)

    await artists.create_index("name")
    await artists.create_index("slug", unique=True)
    await _drop_index_if_exists(artists, "musicbrainz_id_1")
    await artists.create_index(
        "musicbrainz_id",
        unique=True,
        partialFilterExpression={"musicbrainz_id": {"$type": "string"}},
    )
    await artists.create_index("genres")

    albums = db.albums
    await albums.update_many({"musicbrainz_release_id": None}, {"$unset": {"musicbrainz_release_id": ""}})
    await albums.create_index("title")
    await albums.create_index("slug")
    await albums.create_index("artist_id")
    await _drop_index_if_exists(albums, "musicbrainz_release_id_1")
    await albums.create_index(
        "musicbrainz_release_id",
        unique=True,
        partialFilterExpression={"musicbrainz_release_id": {"$type": "string"}},
    )
    await albums.create_index("release_date")

    genres = db.genres
    await genres.create_index("slug", unique=True)
    await genres.create_index("name")

    playback_sources = db.playback_sources
    await playback_sources.create_index("track_id")
    await playback_sources.create_index(
        [("provider", 1), ("provider_track_id", 1)],
        unique=True,
    )

    catalog_imports = db.catalog_imports
    await catalog_imports.create_index("provider")
    await catalog_imports.create_index("started_at")
