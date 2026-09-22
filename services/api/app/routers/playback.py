from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.db import PlayEvent

router = APIRouter(tags=["playback"])


class PlayEventIn(BaseModel):
    track_id: str
    event_type: str = Field(
        description="PLAY|SKIP|REPLAY|LIKE|DISLIKE|COMPLETE_TRACK|..."
    )
    user_id: Optional[str] = None
    position_ms: Optional[int] = None


class PlayEventOut(BaseModel):
    id: str
    accepted: bool
    created_at: datetime


@router.post("/playback/events", response_model=PlayEventOut)
async def record_play_event(body: PlayEventIn, db: AsyncSession = Depends(get_db)):
    event = PlayEvent(
        user_id=body.user_id,
        track_id=body.track_id,
        event_type=body.event_type.upper(),
        position_ms=body.position_ms,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return PlayEventOut(id=event.id, accepted=True, created_at=event.created_at)


@router.get("/playback/session")
async def get_playback_session(user_id: Optional[str] = None):
    """Synced playback state — Redis-backed in a later iteration."""
    return {
        "user_id": user_id,
        "track_id": None,
        "position_ms": 0,
        "is_playing": False,
        "queue": [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "backend": "memory-stub",
    }
