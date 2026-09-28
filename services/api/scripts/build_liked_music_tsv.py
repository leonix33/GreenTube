"""Build liked_music_targets.tsv from a YouTube Music-style paste (title, artist, album, duration blocks)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

DURATION = re.compile(r"^\d{1,2}:\d{2}$")
SKIP_ARTISTS = {
    "watchverse",
    "justnaija",
    "trendybeatz",
    "mariodrilly",
    "tethered visuals",
    "vibe music",
    "mujeeb o.f",
    "worldstarhiphop",
    "futurehype",
    "lyrical field",
    "tydollasignofficial",
    "official video",
    "sms",
    "iamobas",
    "spothim",
}
SKIP_TITLE = re.compile(
    r"(official video|official music video|lyrics\)|closed caption|\[official|visualizer\)|"
    r"spring mix|afrobeats 20\d\d mix|prod\.|dance video)",
    re.I,
)
GENRE_HEADER = {
    "party",
    "romance",
    "chill",
    "hip-hop",
    "afrobeats",
    "rhythm and blues",
    "pump-up",
    "afroswing",
    "nigerian hip hop",
    "nigerian r&b",
    "downbeat",
    "pop music",
    "upbeat",
    "nigerian alté",
    "workout",
}


def _clean_artist(line: str) -> str:
    line = line.strip().strip(",").strip()
    if line.startswith(","):
        line = line[1:].strip()
    return line.split(",")[0].split("&")[0].strip()


def parse_export(text: str) -> list[tuple[str, str]]:
    lines = [ln.strip() for ln in text.splitlines()]
    blocks: list[list[str]] = []
    current: list[str] = []
    for ln in lines:
        if DURATION.match(ln):
            if current:
                blocks.append(current)
                current = []
            continue
        if not ln or ln == "Player":
            continue
        current.append(ln)
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for block in blocks:
        if len(block) < 2:
            continue
        title = block[0]
        artist = _clean_artist(block[1])
        if not title or not artist:
            continue
        if title.lower() in GENRE_HEADER:
            continue
        if artist.lower() in SKIP_ARTISTS:
            continue
        if SKIP_TITLE.search(title):
            continue
        if re.match(r"^\d{1,2}:\d{2}$", title):
            continue
        key = (title.casefold(), artist.casefold())
        if key in seen:
            continue
        seen.add(key)
        out.append((title, artist))
    return out


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    src = root / "data" / "liked_music_export.txt"
    dst = root / "data" / "liked_music_targets.tsv"
    if len(sys.argv) > 1:
        src = Path(sys.argv[1])
    text = src.read_text(encoding="utf-8")
    pairs = parse_export(text)
    lines = [f"{t}\t{a}" for t, a in pairs]
    dst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(pairs)} tracks to {dst}")


if __name__ == "__main__":
    main()
