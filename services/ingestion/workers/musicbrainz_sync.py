"""
MusicBrainz metadata sync stub.

Respect MusicBrainz rate limits and identify with a proper User-Agent.
This worker only ingests *metadata* into the canonical catalog — not commercial audio.
"""

from __future__ import annotations

import os
import time

import httpx

USER_AGENT = os.getenv(
    "MUSICBRAINZ_USER_AGENT",
    "GreenTubeMusic/0.1.0 (https://github.com/leonix33/GreenTube)",
)
MB_BASE = "https://musicbrainz.org/ws/2"


def search_recordings(query: str, limit: int = 5) -> list[dict]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    params = {"query": query, "fmt": "json", "limit": limit}
    with httpx.Client(timeout=30.0, headers=headers) as client:
        # MusicBrainz: ~1 request/second for anonymous clients
        time.sleep(1.1)
        resp = client.get(f"{MB_BASE}/recording", params=params)
        resp.raise_for_status()
        return resp.json().get("recordings", [])


def main() -> None:
    print("GreenTube ingestion worker (MusicBrainz metadata stub)")
    print(f"User-Agent: {USER_AGENT}")
    sample = search_recordings("artist:radiohead AND recording:creep", limit=3)
    for rec in sample:
        title = rec.get("title")
        mbid = rec.get("id")
        print(f"  - {title} [{mbid}]")
    print("Done. Wire normalize + Postgres upsert next.")


if __name__ == "__main__":
    main()
