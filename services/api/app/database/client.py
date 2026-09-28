from __future__ import annotations

from typing import Any, Optional

import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None
_last_error: Optional[str] = None


async def connect_mongodb(uri: str, database_name: str) -> bool:
    """Connect on application startup. Returns False if URI missing or unreachable."""
    global _client, _db, _last_error
    await close_mongodb()

    if not uri or not uri.strip():
        _last_error = "MONGODB_URI not configured"
        return False

    try:
        client = AsyncIOMotorClient(
            uri.strip(),
            serverSelectionTimeoutMS=4000,
            tlsCAFile=certifi.where(),
        )
        await client.admin.command("ping")
        _client = client
        _db = client[database_name]
        _last_error = None
        return True
    except Exception as exc:  # noqa: BLE001 — surface message in health
        _client = None
        _db = None
        _last_error = str(exc)
        return False


async def close_mongodb() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


def get_catalog_db() -> Optional[AsyncIOMotorDatabase]:
    return _db


def is_mongodb_connected() -> bool:
    return _db is not None


def mongodb_health() -> dict[str, Any]:
    return {
        "connected": is_mongodb_connected(),
        "error": _last_error,
    }
