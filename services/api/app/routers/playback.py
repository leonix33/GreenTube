from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.db.session import try_db
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
    id: Optional[str] = None
    accepted: bool
    created_at: datetime
    persisted: bool = False


@router.post("/playback/events", response_model=PlayEventOut)
async def record_play_event(body: PlayEventIn):
    db = await try_db()
    if db is None:
        return PlayEventOut(
            id=None,
            accepted=True,
            created_at=datetime.now(timezone.utc),
            persisted=False,
        )
    try:
        event = PlayEvent(
            user_id=body.user_id,
            track_id=body.track_id,
            event_type=body.event_type.upper(),
            position_ms=body.position_ms,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return PlayEventOut(
            id=event.id,
            accepted=True,
            created_at=event.created_at,
            persisted=True,
        )
    except Exception:
        await db.rollback()
        return PlayEventOut(
            id=None,
            accepted=True,
            created_at=datetime.now(timezone.utc),
            persisted=False,
        )
    finally:
        await db.close()


@router.get("/playback/session")
async def get_playback_session(user_id: Optional[str] = None):
    return {
        "user_id": user_id,
        "track_id": None,
        "position_ms": 0,
        "is_playing": False,
        "queue": [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "backend": "memory-stub",
    }
