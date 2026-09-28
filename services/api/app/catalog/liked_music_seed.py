"""Leonix Liked Music — target tracks loaded from data/liked_music_targets.tsv."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_DATA = Path(__file__).resolve().parents[2] / "data" / "liked_music_targets.tsv"
_PART_SIZE = 45


@dataclass(frozen=True)
class TargetTrack:
    title: str
    artist: str
    search_queries: tuple[str, ...] = ()


def _q(title: str, artist: str, *extra: str) -> tuple[str, ...]:
    base = (f"{artist} {title}".strip(), title, artist.split(",")[0].strip())
    return base + extra


def _load_pairs() -> list[tuple[str, str]]:
    if not _DATA.is_file():
        return []
    pairs: list[tuple[str, str]] = []
    for line in _DATA.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" in line:
            title, artist = line.split("\t", 1)
        else:
            title, _, artist = line.partition("|")
        title, artist = title.strip(), artist.strip()
        if title and artist:
            pairs.append((title, artist))
    return pairs


def _to_target(title: str, artist: str) -> TargetTrack:
    return TargetTrack(title, artist, _q(title, artist))


def _all_targets() -> tuple[TargetTrack, ...]:
    return tuple(_to_target(t, a) for t, a in _load_pairs())


LIKED_MUSIC_ALL = _all_targets()

LIKED_MUSIC_PARTS: dict[int, tuple[TargetTrack, ...]] = {}
for i in range(0, max(len(LIKED_MUSIC_ALL), 1), _PART_SIZE):
    part_num = i // _PART_SIZE + 1
    LIKED_MUSIC_PARTS[part_num] = LIKED_MUSIC_ALL[i : i + _PART_SIZE]

# Backward compat
LIKED_MUSIC_PART_1 = LIKED_MUSIC_PARTS.get(1, ())


def targets_for_part(part: int) -> tuple[TargetTrack, ...]:
    if part not in LIKED_MUSIC_PARTS:
        raise KeyError(f"Unknown liked music part {part}")
    return LIKED_MUSIC_PARTS[part]


PLAYLIST_ID = "liked-music-leonix"
PLAYLIST_TITLE = "Liked Music"
PLAYLIST_DESCRIPTION = (
    "Your YouTube Music Liked library — matched to playable tracks on GreenTube (Audius)."
)

LIKED_MUSIC_TARGETS = LIKED_MUSIC_ALL
