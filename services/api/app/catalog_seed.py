"""Deterministic demo catalog: open/user-owned audio we generate locally (no third-party scrape)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

STATIC_AUDIO = Path(__file__).resolve().parent.parent / "static" / "audio"


@dataclass(frozen=True)
class GenreInfo:
    slug: str
    name: str


@dataclass(frozen=True)
class SeedTrack:
    id: str
    title: str
    artist: str
    album: str
    duration_ms: int
    genres: list[str]
    filename: str
    provider: str = "open"

    @property
    def stream_path(self) -> str:
        return f"/static/audio/{self.filename}"


# Browse taxonomy — shown on Explore even before full catalog ingest.
GENRES: list[GenreInfo] = [
    GenreInfo("afrobeats", "Afrobeats"),
    GenreInfo("hip-hop", "Hip-Hop"),
    GenreInfo("rnb", "R&B"),
    GenreInfo("pop", "Pop"),
    GenreInfo("rock", "Rock"),
    GenreInfo("indie", "Indie"),
    GenreInfo("electronic", "Electronic"),
    GenreInfo("house", "House"),
    GenreInfo("techno", "Techno"),
    GenreInfo("jazz", "Jazz"),
    GenreInfo("blues", "Blues"),
    GenreInfo("soul", "Soul"),
    GenreInfo("funk", "Funk"),
    GenreInfo("classical", "Classical"),
    GenreInfo("ambient", "Ambient"),
    GenreInfo("chill", "Chill"),
    GenreInfo("focus", "Focus"),
    GenreInfo("latin", "Latin"),
    GenreInfo("reggae", "Reggae"),
    GenreInfo("dancehall", "Dancehall"),
    GenreInfo("country", "Country"),
    GenreInfo("folk", "Folk"),
    GenreInfo("gospel", "Gospel"),
    GenreInfo("metal", "Metal"),
    GenreInfo("punk", "Punk"),
    GenreInfo("k-pop", "K-Pop"),
    GenreInfo("world", "World"),
    GenreInfo("soundtrack", "Soundtrack"),
    GenreInfo("workout", "Workout"),
    GenreInfo("late-night", "Late Night"),
    GenreInfo("instrumental", "Instrumental"),
]

SEED_TRACKS: list[SeedTrack] = [
    SeedTrack(
        id="11111111-1111-1111-1111-111111111101",
        title="Lagos Pulse",
        artist="Green Room Ensemble",
        album="Open Circuit Vol. 1",
        duration_ms=28_000,
        genres=["afrobeats", "electronic", "pop"],
        filename="lagos-pulse.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111102",
        title="Charcoal Evening",
        artist="North Harbor",
        album="After Hours",
        duration_ms=32_000,
        genres=["ambient", "electronic", "chill", "late-night"],
        filename="charcoal-evening.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111103",
        title="Paper Lanterns",
        artist="Mira Chen",
        album="Soft Circuits",
        duration_ms=26_000,
        genres=["indie", "instrumental", "folk"],
        filename="paper-lanterns.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111104",
        title="Dust & Chrome",
        artist="Kiln",
        album="Foundry",
        duration_ms=30_000,
        genres=["electronic", "focus", "techno"],
        filename="dust-chrome.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111105",
        title="Sunday Market",
        artist="Kofi Mensah",
        album="Open Air",
        duration_ms=34_000,
        genres=["afrobeats", "world", "gospel"],
        filename="sunday-market.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111106",
        title="Green Signal",
        artist="Platform Tone",
        album="Demo Beds",
        duration_ms=24_000,
        genres=["focus", "instrumental"],
        filename="green-signal.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111107",
        title="Miami Heatline",
        artist="DJ Sol Verde",
        album="Coastal FM",
        duration_ms=29_000,
        genres=["hip-hop", "latin", "funk"],
        filename="miami-heatline.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111108",
        title="Velvet Room",
        artist="Amara Cole",
        album="Midnight Suite",
        duration_ms=31_000,
        genres=["rnb", "soul", "late-night"],
        filename="velvet-room.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111109",
        title="Blue Hour",
        artist="The Ellington Line",
        album="Smoky Glass",
        duration_ms=33_000,
        genres=["jazz", "blues", "instrumental"],
        filename="blue-hour.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111110",
        title="Cathedral Echo",
        artist="Nova Strings",
        album="Hall Light",
        duration_ms=27_000,
        genres=["classical", "ambient", "soundtrack"],
        filename="cathedral-echo.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111111",
        title="Highway Stereo",
        artist="Rust & Relay",
        album="Open Road",
        duration_ms=28_000,
        genres=["rock", "indie", "punk"],
        filename="highway-stereo.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111112",
        title="Neon District",
        artist="Pulse 88",
        album="After Midnight",
        duration_ms=30_000,
        genres=["house", "techno", "electronic"],
        filename="neon-district.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111113",
        title="Island Crown",
        artist="Irie Collective",
        album="Sunrise Dub",
        duration_ms=32_000,
        genres=["reggae", "dancehall", "world"],
        filename="island-crown.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111114",
        title="Seoul Nights",
        artist="Hana Park",
        album="City Glow",
        duration_ms=26_000,
        genres=["k-pop", "pop", "electronic"],
        filename="seoul-nights.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111115",
        title="Iron Pulse",
        artist="Forge Nine",
        album="Heavy Circuit",
        duration_ms=25_000,
        genres=["metal", "rock", "workout"],
        filename="iron-pulse.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111116",
        title="Prairie Light",
        artist="Willow Hart",
        album="Dust & Honey",
        duration_ms=29_000,
        genres=["country", "folk"],
        filename="prairie-light.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111117",
        title="Accra Sunrise",
        artist="Voices of Light",
        album="Sanctuary",
        duration_ms=35_000,
        genres=["gospel", "afrobeats", "soul"],
        filename="accra-sunrise.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111118",
        title="Low Tide",
        artist="Coastal Forms",
        album="Drift",
        duration_ms=34_000,
        genres=["chill", "ambient", "late-night"],
        filename="low-tide.wav",
    ),
]


def track_by_id(track_id: str) -> SeedTrack | None:
    return next((t for t in SEED_TRACKS if t.id == track_id), None)


def tracks_for_genre(slug: str) -> list[SeedTrack]:
    key = slug.lower().strip()
    return [t for t in SEED_TRACKS if key in t.genres]


def genre_track_counts() -> dict[str, int]:
    counts: dict[str, int] = {g.slug: 0 for g in GENRES}
    for track in SEED_TRACKS:
        for slug in track.genres:
            counts[slug] = counts.get(slug, 0) + 1
    return counts


def ensure_demo_audio() -> None:
    """Generate short original WAV tones (public-domain style demo assets we own)."""
    import math
    import struct
    import wave

    STATIC_AUDIO.mkdir(parents=True, exist_ok=True)

    specs = [
        ("lagos-pulse.wav", 220.0, 28.0, 0.25),
        ("charcoal-evening.wav", 164.81, 32.0, 0.2),
        ("paper-lanterns.wav", 293.66, 26.0, 0.22),
        ("dust-chrome.wav", 196.0, 30.0, 0.18),
        ("sunday-market.wav", 246.94, 34.0, 0.24),
        ("green-signal.wav", 329.63, 24.0, 0.2),
        ("miami-heatline.wav", 207.65, 29.0, 0.23),
        ("velvet-room.wav", 174.61, 31.0, 0.21),
        ("blue-hour.wav", 155.56, 33.0, 0.19),
        ("cathedral-echo.wav", 130.81, 27.0, 0.2),
        ("highway-stereo.wav", 246.94, 28.0, 0.24),
        ("neon-district.wav", 220.0, 30.0, 0.22),
        ("island-crown.wav", 196.0, 32.0, 0.23),
        ("seoul-nights.wav", 277.18, 26.0, 0.22),
        ("iron-pulse.wav", 146.83, 25.0, 0.26),
        ("prairie-light.wav", 185.0, 29.0, 0.2),
        ("accra-sunrise.wav", 233.08, 35.0, 0.24),
        ("low-tide.wav", 164.81, 34.0, 0.18),
    ]

    sample_rate = 22050
    for filename, freq, seconds, volume in specs:
        path = STATIC_AUDIO / filename
        if path.exists() and path.stat().st_size > 1000:
            continue
        n_samples = int(sample_rate * seconds)
        with wave.open(str(path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            frames = bytearray()
            for i in range(n_samples):
                t = i / sample_rate
                env = min(1.0, t * 4) * min(1.0, (seconds - t) * 4)
                sample = (
                    math.sin(2 * math.pi * freq * t) * 0.7
                    + math.sin(2 * math.pi * freq * 1.5 * t) * 0.3
                ) * volume * env
                frames.extend(struct.pack("<h", int(max(-1, min(1, sample)) * 32767)))
            wf.writeframes(frames)
