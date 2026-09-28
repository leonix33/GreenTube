import pytest

from app.providers.local import LocalCatalogProvider


@pytest.mark.asyncio
async def test_local_provider_import_all_seed_tracks():
    provider = LocalCatalogProvider()
    rows = await provider.import_tracks(limit=1000)
    assert len(rows) >= 18
    assert rows[0]["playback"]["available"] is True
    assert rows[0]["source"]["provider"] == "local"
