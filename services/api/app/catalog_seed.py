"""Deterministic demo catalog: open/user-owned audio we generate locally (no third-party scrape)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

STATIC_AUDIO = Path(__file__).resolve().parent.parent / "static" / "audio"


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


SEED_TRACKS: list[SeedTrack] = [
    SeedTrack(
        id="11111111-1111-1111-1111-111111111101",
        title="Lagos Pulse",
        artist="Green Room Ensemble",
        album="Open Circuit Vol. 1",
        duration_ms=28_000,
        genres=["afrobeats", "electronic"],
        filename="lagos-pulse.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111102",
        title="Charcoal Evening",
        artist="North Harbor",
        album="After Hours",
        duration_ms=32_000,
        genres=["ambient", "electronic"],
        filename="charcoal-evening.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111103",
        title="Paper Lanterns",
        artist="Mira Chen",
        album="Soft Circuits",
        duration_ms=26_000,
        genres=["indie", "instrumental"],
        filename="paper-lanterns.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111104",
        title="Dust & Chrome",
        artist="Kiln",
        album="Foundry",
        duration_ms=30_000,
        genres=["electronic", "focus"],
        filename="dust-chrome.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111105",
        title="Sunday Market",
        artist="Kofi Mensah",
        album="Open Air",
        duration_ms=34_000,
        genres=["afrobeats", "world"],
        filename="sunday-market.wav",
    ),
    SeedTrack(
        id="11111111-1111-1111-1111-111111111106",
        title="Green Signal",
        artist="Platform Tone",
        album="Demo Beds",
        duration_ms=24_000,
        genres=["focus"],
        filename="green-signal.wav",
    ),
]


def track_by_id(track_id: str) -> SeedTrack | None:
    return next((t for t in SEED_TRACKS if t.id == track_id), None)


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
                # Soft envelope + slight harmony so it isn't a raw beep
                env = min(1.0, t * 4) * min(1.0, (seconds - t) * 4)
                sample = (
                    math.sin(2 * math.pi * freq * t) * 0.7
                    + math.sin(2 * math.pi * freq * 1.5 * t) * 0.3
                ) * volume * env
                frames.extend(struct.pack("<h", int(max(-1, min(1, sample)) * 32767)))
            wf.writeframes(frames)
