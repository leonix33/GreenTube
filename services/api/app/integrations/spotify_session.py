"""Mongo-backed browser session for Spotify OAuth tokens."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def get_session(db: AsyncIOMotorDatabase, session_id: str) -> dict[str, Any] | None:
    return await db.integration_sessions.find_one({"session_id": session_id})


async def upsert_spotify_tokens(
    db: AsyncIOMotorDatabase,
    session_id: str,
    *,
    access_token: str,
    refresh_token: str | None,
    expires_at: datetime,
    scope: str,
) -> None:
    await db.integration_sessions.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "session_id": session_id,
                "spotify": {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expires_at": expires_at,
                    "scope": scope,
                    "updated_at": utcnow(),
                },
                "updated_at": utcnow(),
            },
            "$setOnInsert": {"created_at": utcnow()},
        },
        upsert=True,
    )


async def spotify_tokens(db: AsyncIOMotorDatabase, session_id: str) -> dict[str, Any] | None:
    doc = await get_session(db, session_id)
    if not doc:
        return None
    return doc.get("spotify")
