from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CatalogProvider(ABC):
    name: str

    @abstractmethod
    async def search_tracks(self, query: str, *, limit: int = 25) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def import_tracks(
        self,
        *,
        query: str | None = None,
        genre: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """Return normalized track documents ready for ingestion (not yet persisted)."""
        raise NotImplementedError

    async def get_track(self, provider_track_id: str) -> dict[str, Any] | None:
        return None

    async def get_artist(self, provider_artist_id: str) -> dict[str, Any] | None:
        return None

    async def get_album(self, provider_album_id: str) -> dict[str, Any] | None:
        return None

    async def get_genres(self) -> list[dict[str, Any]]:
        return []
