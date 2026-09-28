"""Score Audius (normalized) tracks against a target title + artist."""

from __future__ import annotations

import re
import unicodedata

from app.catalog.liked_music_seed import TargetTrack
from app.config import get_settings

STOP = re.compile(
    r"\(official|\(lyrics\)|\[official|watchverse|justnaija|trendybeatz|mariodrilly",
    re.I,
)
BOOTLEG = re.compile(
    r"prenkoloaded|naijaloaded|mp3_\d+|_com_mp3|notofficial|free\s*download|"
    r"type\s*beat|free\s*beat|\bstems?\b|\(free\)",
    re.I,
)
MIXTAPE = re.compile(
    r"mixtape|mega\s*mix|dj\s*mix|nonstop|non-stop|spring\s*mix|club\s*mix|"
    r"afrobeats\s*20\d{2}|best\s*of\s*20\d{2}|\bplaylist\b|compilation|"
    r"\b\d+\s*hour|\bnon.?stop\b|type\s*beat|free\s*beat|instrumental\s*only",
    re.I,
)
DJ_UPLOADER = re.compile(
    r"^dj\s|\bdj\s+\w|djemz|dj\s*boat|mujeeb|official\s*koko",
    re.I,
)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _norm_title_match(s: str) -> str:
    """Ignore feat./with credits when comparing song titles."""
    s = re.sub(r"\(feat[^)]*\)", " ", s or "", flags=re.I)
    s = re.sub(r"\(with[^)]*\)", " ", s, flags=re.I)
    s = re.sub(r"\bfeat\.?\s+[^)]+", " ", s, flags=re.I)
    return _norm(s)


def _tokens(s: str) -> set[str]:
    return {t for t in _norm(s).split() if len(t) > 1}


def target_wants_remix(target: TargetTrack) -> bool:
    return "remix" in _norm(target.title)


def originality_penalty(
    target: TargetTrack,
    title: str,
    artist: str,
    *,
    duration_seconds: int | None = None,
) -> float:
    """Higher = worse; >= 10 means reject."""
    if MIXTAPE.search(title or "") or BOOTLEG.search(title or ""):
        return 10.0
    if STOP.search(title or ""):
        return 10.0
    ntitle = _norm(title or "")
    if "remix" in ntitle and not target_wants_remix(target):
        return 2.5
    if "house remix" in ntitle or "jrnd" in ntitle:
        return 3.0
    if "acoustic" in ntitle and "acoustic" not in _norm(target.title):
        return 1.5
    if "live" in ntitle and "live" not in _norm(target.title):
        return 1.0
    if DJ_UPLOADER.search(artist or "") and not DJ_UPLOADER.search(target.artist):
        return 2.0
    if duration_seconds and duration_seconds > 480:
        return 3.0
    return 0.0


def candidate_from_doc(doc: dict) -> dict:
    return {
        "title": doc.get("title"),
        "artist": doc.get("artist"),
        "duration_seconds": doc.get("duration_seconds"),
        "source": doc.get("source"),
        "playback": doc.get("playback"),
    }


def match_score(target: TargetTrack, title: str, artist: str) -> float:
    if STOP.search(title or "") or BOOTLEG.search(title or ""):
        return 0.0
    nt = _norm_title_match(target.title)
    na = _norm(target.artist)
    ntitle = _norm_title_match(title or "")
    nartist = _norm(artist or "")

    title_toks = _tokens(target.title)
    track_toks = _tokens(title or "")
    artist_toks = _tokens(target.artist)

    if not title_toks:
        return 0.0

    title_overlap = len(title_toks & track_toks) / len(title_toks)
    if nt in ntitle or ntitle in nt:
        title_overlap = max(title_overlap, 0.85)

    artist_overlap = 0.0
    if na in nartist or na in ntitle or any(t in nartist or t in ntitle for t in artist_toks):
        artist_overlap = 1.0
    elif artist_toks & (_tokens(artist) | track_toks):
        artist_overlap = 0.5

    if title_overlap < 0.4:
        return 0.0
    if artist_overlap < 0.35:
        return 0.0
    return title_overlap * 0.65 + artist_overlap * 0.35


def _loose_title_artist_in_title(target: TargetTrack, title: str) -> float:
    """Fan uploads often put the star name in the title, not the uploader name."""
    if STOP.search(title or ""):
        return 0.0
    ntitle = _norm(title or "")
    title_toks = _tokens(target.title)
    artist_toks = _tokens(target.artist)
    if not title_toks:
        return 0.0
    overlap = len(title_toks & _tokens(title)) / len(title_toks)
    if overlap < 0.5:
        return 0.0
    if not any(t in ntitle for t in artist_toks):
        return 0.0
    return overlap


def match_score_deezer(target: TargetTrack, title: str, artist: str) -> float:
    """Canonical artist/title from Deezer — stricter than Audius fan uploads."""
    nt = _norm_title_match(target.title)
    na = _norm(target.artist)
    ntitle = _norm_title_match(title or "")
    nartist = _norm(artist or "")
    if not nt:
        return 0.0
    title_toks = _tokens(target.title)
    overlap = len(title_toks & _tokens(title)) / len(title_toks) if title_toks else 0.0
    if nt in ntitle or ntitle in nt:
        overlap = max(overlap, 0.9)
    artist_ok = na in nartist or nartist in na or bool(_tokens(target.artist) & _tokens(artist))
    # Deezer often lists a featured artist as primary on collab singles.
    if not artist_ok and overlap >= 0.85:
        artist_ok = True
    if not artist_ok:
        return 0.0
    if nt == ntitle:
        return 1.0
    if overlap < 0.55:
        return 0.0
    return 0.7 + overlap * 0.3


def best_match(
    target: TargetTrack,
    candidates: list[dict],
    *,
    min_score: float = 0.48,
    provider: str | None = None,
) -> dict | None:
    best: dict | None = None
    best_s = 0.0
    use_deezer = provider == "deezer"
    floor = 0.72 if use_deezer else min_score
    for c in candidates:
        title = c.get("title") or ""
        artist = (c.get("artist") or {}).get("name") or ""
        if use_deezer:
            s = match_score_deezer(target, title, artist)
        else:
            s = match_score(target, title, artist)
            if s <= 0:
                s = _loose_title_artist_in_title(target, title)
        if s > best_s:
            best_s = s
            best = c
    if best_s >= floor:
        return best
    return None


async def fetch_liked_candidates(
    target: TargetTrack,
    *,
    audius,
    jamendo,
    deezer,
    include_deezer: bool | None = None,
) -> list[dict]:
    """Search Audius, optional Jamendo, then Deezer previews."""
    candidates: list[dict] = []
    queries = list(target.search_queries or (f"{target.artist} {target.title}",))
    queries.extend(
        [
            target.title,
            f"{target.artist} {target.title}",
            target.artist,
        ]
    )
    if include_deezer is None:
        include_deezer = get_settings().allow_preview_playback
    seen_q: set[str] = set()
    for q in queries:
        q = q.strip()
        if not q or q.lower() in seen_q:
            continue
        seen_q.add(q.lower())
        try:
            candidates.extend(await audius.import_tracks(query=q, limit=40))
        except Exception:
            pass
        if getattr(jamendo, "configured", False):
            try:
                candidates.extend(await jamendo.import_tracks(query=q, limit=25))
            except Exception:
                pass
        if include_deezer:
            try:
                candidates.extend(await deezer.import_tracks(query=q, limit=15))
            except Exception:
                pass
    return candidates


def score_candidate(target: TargetTrack, candidate: dict) -> float:
    title = candidate.get("title") or ""
    artist = (candidate.get("artist") or {}).get("name") or ""
    prov = (candidate.get("source") or {}).get("provider") or ""
    dur = candidate.get("duration_seconds")
    try:
        dur_i = int(dur) if dur is not None else None
    except (TypeError, ValueError):
        dur_i = None

    pen = originality_penalty(target, title, artist, duration_seconds=dur_i)
    if pen >= 10:
        return 0.0

    if prov == "deezer":
        if not get_settings().allow_preview_playback:
            return 0.0
        base = match_score_deezer(target, title, artist)
    else:
        base = match_score(target, title, artist)
        if base <= 0:
            base = _loose_title_artist_in_title(target, title)
    if base <= 0:
        return 0.0

    if prov in ("audius", "jamendo", "local") and pen == 0 and base >= 0.62:
        base += 0.1
    elif prov == "deezer" and pen == 0:
        base += 0.05

    return max(0.0, base - pen * 0.2)


def pick_best_for_target(target: TargetTrack, candidates: list[dict]) -> dict | None:
    """Best studio-like match across providers (mixtapes/DJ sets penalized)."""
    best: dict | None = None
    best_s = 0.0
    for c in candidates:
        s = score_candidate(target, c)
        if s > best_s:
            best_s = s
            best = c
    if best_s >= 0.68:
        return best
    return None


def is_acceptable_liked_match(target: TargetTrack, candidate: dict) -> bool:
    title = candidate.get("title") or ""
    artist = (candidate.get("artist") or {}).get("name") or ""
    dur = candidate.get("duration_seconds")
    try:
        dur_i = int(dur) if dur is not None else None
    except (TypeError, ValueError):
        dur_i = None
    if originality_penalty(target, title, artist, duration_seconds=dur_i) >= 1.0:
        return False
    prov = (candidate.get("source") or {}).get("provider")
    floor = 0.68 if prov == "deezer" else 0.72
    return score_candidate(target, candidate) >= floor
