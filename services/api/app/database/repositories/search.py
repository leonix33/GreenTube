from __future__ import annotations

import re
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase


class CatalogSearchRepository:
    """
    MongoDB-backed search (regex today; structured for Atlas Search upgrade later).
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._tracks = db.tracks
        self._artists = db.artists
        self._albums = db.albums
        self._genres = db.genres

    @staticmethod
    def _pattern(q: str) -> re.Pattern[str]:
        escaped = re.escape(q.strip())
        return re.compile(escaped, re.IGNORECASE)

    async def search(
        self,
        q: str,
        *,
        limit: int = 20,
        playable_only_for_tracks: bool = True,
    ) -> dict[str, list[dict[str, Any]]]:
        if not q.strip():
            return {"tracks": [], "artists": [], "albums": [], "genres": []}

        pattern = self._pattern(q)

        track_query: dict[str, Any] = {
            "$or": [
                {"title": pattern},
                {"artist.name": pattern},
                {"album.title": pattern},
                {"genres": pattern},
            ]
        }
        if playable_only_for_tracks:
            track_query["playback.available"] = True

        tracks = await self._tracks.find(track_query).limit(limit).to_list(length=limit)
        artists = await self._artists.find({"name": pattern}).limit(limit).to_list(length=limit)
        albums = await self._albums.find({"title": pattern}).limit(limit).to_list(length=limit)
        genres = await self._genres.find(
            {"$or": [{"name": pattern}, {"slug": pattern}]}
        ).limit(limit).to_list(length=limit)

        return {
            "tracks": tracks,
            "artists": artists,
            "albums": albums,
            "genres": genres,
        }
