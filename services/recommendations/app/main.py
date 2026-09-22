"""GreenTube recommendation service — weighted affinity v0."""

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="GreenTube Recommendations", version="0.1.0")


class RadioRequest(BaseModel):
    seed_track_id: str | None = None
    seed_artist_id: str | None = None
    limit: int = Field(default=30, le=100)


class NlPlaylistRequest(BaseModel):
    prompt: str
    duration_minutes: int | None = None


@app.get("/health")
async def health():
    return {"status": "ok", "service": "green-tube-recommendations"}


@app.post("/radio")
async def radio(body: RadioRequest):
    """v0 stub: returns empty slate until embeddings + play signals exist."""
    return {
        "seed_track_id": body.seed_track_id,
        "seed_artist_id": body.seed_artist_id,
        "track_ids": [],
        "strategy": "weighted_affinity_v0_stub",
    }


@app.get("/mixes/{user_id}")
async def mixes(user_id: str):
    return {
        "user_id": user_id,
        "mixes": [
            {"id": "my-mix-1", "title": "My Mix 1", "track_ids": []},
            {"id": "discover", "title": "Discover Mix", "track_ids": []},
            {"id": "new-release", "title": "New Release Mix", "track_ids": []},
        ],
    }


@app.post("/nl-playlist")
async def nl_playlist(body: NlPlaylistRequest):
    """Translate natural language into catalog/recommendation query plan."""
    return {
        "prompt": body.prompt,
        "duration_minutes": body.duration_minutes,
        "plan": {
            "filters": [],
            "exclude_recent_days": 7,
            "notes": "Parser + ranker not wired yet — returns query plan stub.",
        },
        "track_ids": [],
    }
