from app.providers.audius import AudiusCatalogProvider
from app.providers.deezer import DeezerCatalogProvider
from app.providers.jamendo import JamendoCatalogProvider
from app.providers.local import LocalCatalogProvider
from app.providers.musicbrainz import MusicBrainzCatalogProvider

__all__ = [
    "AudiusCatalogProvider",
    "DeezerCatalogProvider",
    "JamendoCatalogProvider",
    "LocalCatalogProvider",
    "MusicBrainzCatalogProvider",
]
