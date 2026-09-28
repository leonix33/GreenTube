from __future__ import annotations

import re
from typing import Any


def slugify(value: str) -> str:
    text = value.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "untitled"


def normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def dedupe_fingerprint(artist_name: str, title: str, duration_seconds: int | None) -> str:
    artist = normalize_title(artist_name)
    title_n = normalize_title(title)
    dur = duration_seconds if duration_seconds is not None else -1
    return f"{artist}|{title_n}|{dur}"


def strip_none(document: dict[str, Any]) -> dict[str, Any]:
    """Remove None values one level deep for cleaner Mongo updates."""
    return {k: v for k, v in document.items() if v is not None}
