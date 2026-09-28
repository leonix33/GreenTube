"""Seed local demo catalog into MongoDB Atlas."""

from __future__ import annotations

import asyncio

from app.catalog.seed_local import seed_local_catalog
from app.config import get_settings
from app.database.client import close_mongodb, connect_mongodb, get_catalog_db
from app.database.indexes import ensure_catalog_indexes


async def main() -> None:
    settings = get_settings()
    ok = await connect_mongodb(settings.mongodb_uri, settings.mongodb_database)
    if not ok:
        raise SystemExit("MongoDB unavailable — set MONGODB_URI in services/api/.env")

    db = get_catalog_db()
    assert db is not None
    await ensure_catalog_indexes(db)
    result = await seed_local_catalog(db)
    print(result)
    await close_mongodb()


if __name__ == "__main__":
    asyncio.run(main())
