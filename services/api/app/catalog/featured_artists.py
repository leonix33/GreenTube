"""Curated star artists — match imports and surface them ahead of generic Audius noise."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FeaturedArtist:
    slug: str
    name: str
    match_phrases: tuple[str, ...]
    genres: tuple[str, ...] = ("afrobeats",)


_RAW: tuple[FeaturedArtist, ...] = (
    FeaturedArtist("davido", "Davido", ("davido",)),
    FeaturedArtist("burna-boy", "Burna Boy", ("burna boy", "burna-boy")),
    FeaturedArtist("wizkid", "Wizkid", ("wizkid",)),
    FeaturedArtist("asake", "Asake", ("asake",)),
    FeaturedArtist("rema", "Rema", ("rema",)),
    FeaturedArtist("odumodublvck", "Odumodublvck", ("odumodublvck", "odumodu")),
    FeaturedArtist("ayra-starr", "Ayra Starr", ("ayra starr", "ayra-starr")),
    FeaturedArtist("tiwa-savage", "Tiwa Savage", ("tiwa savage", "tiwa-savage")),
    FeaturedArtist("olamide", "Olamide", ("olamide",)),
    FeaturedArtist("ckay", "CKay", ("ckay",)),
    FeaturedArtist("fireboy-dml", "Fireboy DML", ("fireboy dml", "fireboy")),
    FeaturedArtist("joeboy", "Joeboy", ("joeboy",)),
    FeaturedArtist("omah-lay", "Omah Lay", ("omah lay", "omah-lay")),
    FeaturedArtist("tems", "Tems", ("tems",)),
    FeaturedArtist("kizz-daniel", "Kizz Daniel", ("kizz daniel", "kizz-daniel")),
    FeaturedArtist("shallipopi", "Shallipopi", ("shallipopi",)),
    FeaturedArtist("ruger", "Ruger", ("ruger",)),
    FeaturedArtist("victony", "Victony", ("victony",)),
    FeaturedArtist("spyro", "Spyro", ("spyro",)),
    FeaturedArtist("skepta", "Skepta", ("skepta",), ("afrobeats", "hip-hop")),
    FeaturedArtist("drake", "Drake", ("drake",), ("hip-hop", "pop")),
    FeaturedArtist("nicki-minaj", "Nicki Minaj", ("nicki minaj",), ("hip-hop", "pop")),
    FeaturedArtist("beyonce", "Beyoncé", ("beyonce", "beyoncé"), ("pop", "rnb")),
)

FEATURED_BY_SLUG: dict[str, FeaturedArtist] = {a.slug: a for a in _RAW}
FEATURED_ARTISTS: tuple[FeaturedArtist, ...] = tuple(FEATURED_BY_SLUG.values())

EXCLUDE_TITLE = re.compile(
    r"type\s*beat|instrumental|free\s*beat|freebeat|remix\s*contest|"
    r"afro\s*beat\s*instrumental|\bbeat\s*x\b|\bprod\.?\s*by\b|"
    r"\bcover\b|\bdemo\b|\bsnippet\b|\blyric\s*video\b|\bdj\s|\bmix\b",
    re.IGNORECASE,
)


def _haystack(title: str, artist: str) -> str:
    return f"{title} {artist}".lower()


def match_featured_artist(title: str, artist_name: str) -> FeaturedArtist | None:
    if EXCLUDE_TITLE.search(title or ""):
        return None
    hay = _haystack(title or "", artist_name or "")
    best: FeaturedArtist | None = None
    best_len = 0
    for star in FEATURED_ARTISTS:
        for phrase in star.match_phrases:
            p = phrase.lower()
            if len(p) <= 4:
                found = re.search(rf"\b{re.escape(p)}\b", hay) is not None
            else:
                found = p in hay
            if found and len(p) > best_len:
                best = star
                best_len = len(p)
    return best


def apply_featured_discovery(track: dict, star: FeaturedArtist) -> None:
    disc = track.setdefault("discovery", {})
    disc["featured_artist"] = star.slug
    disc["featured_artist_name"] = star.name
    plays = float((track.get("stats") or {}).get("plays") or 0)
    disc["trending_score"] = 10_000_000 + plays
    for g in star.genres:
        genres = track.setdefault("genres", [])
        if g not in genres:
            genres.append(g)
