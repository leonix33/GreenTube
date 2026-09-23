"""Create schema (if needed) and upsert seed catalog + track_providers."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog_seed import SEED_TRACKS, ensure_demo_audio
from app.db.session import SessionLocal, engine
from app.models.db import Album, Artist, Base, Track, TrackProvider


async def seed(db: AsyncSession) -> None:
    ensure_demo_audio()

    for item in SEED_TRACKS:
        artist = await db.scalar(select(Artist).where(Artist.name == item.artist))
        if not artist:
            artist = Artist(id=str(uuid.uuid4()), name=item.artist)
            db.add(artist)
            await db.flush()

        album = await db.scalar(
            select(Album).where(Album.title == item.album, Album.artist_id == artist.id)
        )
        if not album:
            album = Album(
                id=str(uuid.uuid4()),
                title=item.album,
                artist_id=artist.id,
            )
            db.add(album)
            await db.flush()

        track = await db.scalar(select(Track).where(Track.id == item.id))
        if not track:
            track = Track(
                id=item.id,
                title=item.title,
                album_id=album.id,
                duration_ms=item.duration_ms,
                genres=item.genres,
            )
            db.add(track)
            await db.flush()
        else:
            track.title = item.title
            track.duration_ms = item.duration_ms
            track.genres = item.genres
            track.album_id = album.id

        provider = await db.scalar(
            select(TrackProvider).where(
                TrackProvider.track_id == item.id,
                TrackProvider.provider == item.provider,
            )
        )
        if not provider:
            db.add(
                TrackProvider(
                    id=str(uuid.uuid4()),
                    track_id=item.id,
                    provider=item.provider,
                    provider_track_id=item.filename,
                    playback_type="stream",
                    availability="available",
                    stream_url=item.stream_path,
                )
            )
        else:
            provider.stream_url = item.stream_path
            provider.availability = "available"

    await db.commit()


async def main() -> None:
    # Create tables from ORM as a safety net (compose also loads schema.sql)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # UUID columns in schema.sql use UUID; ORM uses string UUIDs — both fine on PG
        await conn.execute(text("SELECT 1"))

    async with SessionLocal() as db:
        await seed(db)

    print(f"Seeded {len(SEED_TRACKS)} open/demo tracks.")


if __name__ == "__main__":
    asyncio.run(main())
