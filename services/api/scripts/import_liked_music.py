"""Match user's Liked Music list against Mongo + Audius and upsert into Mongo + playlist order."""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone

from app.catalog.dedupe import find_existing_track
from app.catalog.featured_artists import apply_featured_discovery, match_featured_artist
from app.catalog.liked_music_match import (
    candidate_from_doc,
    fetch_liked_candidates,
    is_acceptable_liked_match,
    pick_best_for_target,
    score_candidate,
)
from app.catalog.stream_verify import filter_verified_candidates
from app.config import get_settings
from app.catalog.liked_music_seed import (
    LIKED_MUSIC_PARTS,
    PLAYLIST_DESCRIPTION,
    PLAYLIST_ID,
    PLAYLIST_TITLE,
    TargetTrack,
    targets_for_part,
)
from app.config import get_settings
from app.database.client import close_mongodb, connect_mongodb, get_catalog_db
from app.database.indexes import ensure_catalog_indexes
from app.database.repositories.artists import ArtistRepository
from app.database.repositories.tracks import TrackRepository
from app.providers.audius import AudiusCatalogProvider
from app.providers.deezer import DeezerCatalogProvider
from app.providers.jamendo import JamendoCatalogProvider


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _candidate_from_mongo(doc: dict) -> dict:
    return {
        "title": doc.get("title"),
        "artist": doc.get("artist"),
        "playback": doc.get("playback"),
        "source": doc.get("source"),
        "genres": doc.get("genres"),
        "discovery": doc.get("discovery"),
        "stats": doc.get("stats"),
        "_existing_doc": doc,
    }


async def _mongo_candidates(db, target: TargetTrack, limit: int = 30) -> list[dict]:
    title_key = re.escape(target.title.split()[0][:12])
    artist_key = re.escape(target.artist.split("&")[0].strip().split()[0][:16])
    title_pat = re.compile(title_key, re.IGNORECASE)
    artist_pat = re.compile(artist_key, re.IGNORECASE)
    query = {
        "playback.available": True,
        "title": title_pat,
        "$or": [{"artist.name": artist_pat}, {"title": artist_pat}],
    }
    out: list[dict] = []
    async for doc in db.tracks.find(query).limit(limit):
        out.append(_candidate_from_mongo(doc))
    return out


def _saved_is_full_length(doc: dict) -> bool:
    settings = get_settings()
    playback = doc.get("playback") or {}
    if playback.get("spotify_uri"):
        return True
    prov = (doc.get("source") or {}).get("provider") or ""
    if playback.get("preview_only") or prov == "deezer":
        return settings.allow_preview_playback
    return bool(playback.get("available"))


async def _find_saved(db, target: TargetTrack) -> dict | None:
    best: dict | None = None
    best_s = 0.0
    query = {
        "discovery.liked_music_target.title": target.title,
        "discovery.liked_music_target.artist": target.artist,
        "playback.available": True,
    }
    async for doc in db.tracks.find(query):
        s = score_candidate(target, candidate_from_doc(doc))
        if s > best_s:
            best_s = s
            best = doc
    return best if best_s >= 0.5 else None


async def _clear_other_liked_bindings(db, target: TargetTrack, keep_id) -> None:
    await db.tracks.update_many(
        {
            "discovery.liked_music_target.title": target.title,
            "discovery.liked_music_target.artist": target.artist,
            "_id": {"$ne": keep_id},
        },
        {
            "$unset": {
                "discovery.liked_music_target": "",
                "discovery.playlist_liked_music": "",
            }
        },
    )


async def _import_part(
    part: int,
    *,
    audius: AudiusCatalogProvider,
    jamendo: JamendoCatalogProvider,
    deezer: DeezerCatalogProvider,
    db,
    artists_repo: ArtistRepository,
    tracks_repo: TrackRepository,
    only_misses: bool = False,
    quality_pass: bool = False,
) -> tuple[list[str], list[dict]]:
    targets = targets_for_part(part)
    playlist_track_ids: list[str] = []
    results: list[dict] = []

    for target in targets:
        saved = await _find_saved(db, target)
        if saved and not quality_pass:
            if only_misses:
                playlist_track_ids.append(str(saved["_id"]))
                print(f"SKIP {target.artist} — {target.title}", file=sys.stderr, flush=True)
                continue
            if _saved_is_full_length(saved) and is_acceptable_liked_match(
                target, candidate_from_doc(saved)
            ):
                playlist_track_ids.append(str(saved["_id"]))
                print(f"KEEP {target.artist} — {target.title}", file=sys.stderr, flush=True)
                continue
        elif (
            saved
            and quality_pass
            and _saved_is_full_length(saved)
            and is_acceptable_liked_match(target, candidate_from_doc(saved))
        ):
            playlist_track_ids.append(str(saved["_id"]))
            print(f"KEEP {target.artist} — {target.title}", file=sys.stderr, flush=True)
            continue

        candidates: list[dict] = await _mongo_candidates(db, target)
        settings = get_settings()
        candidates.extend(
            await fetch_liked_candidates(
                target,
                audius=audius,
                jamendo=jamendo,
                deezer=deezer,
                include_deezer=settings.allow_preview_playback,
            )
        )
        verified = await filter_verified_candidates(candidates[:20])
        hit = pick_best_for_target(target, verified)
        row: dict = {
            "target_title": target.title,
            "target_artist": target.artist,
            "matched": False,
        }
        if not hit:
            if saved and quality_pass and is_acceptable_liked_match(
                target, candidate_from_doc(saved)
            ):
                hit = candidate_from_doc(saved)
                hit["_existing_doc"] = saved
            else:
                results.append(row)
                print(f"MISS {target.artist} — {target.title}", file=sys.stderr)
                continue

        if saved and quality_pass and hit.get("_existing_doc") is None:
            old_c = candidate_from_doc(saved)
            if is_acceptable_liked_match(target, old_c):
                old_score = score_candidate(target, old_c)
                new_score = score_candidate(target, hit)
                if new_score <= old_score + 0.05:
                    hit = old_c
                    hit["_existing_doc"] = saved

        existing_doc = hit.pop("_existing_doc", None)
        if existing_doc:
            doc = existing_doc
            tid = str(doc["_id"])
            await db.tracks.update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {
                        "discovery.liked_music_target": {
                            "title": target.title,
                            "artist": target.artist,
                        },
                        "discovery.playlist_liked_music": True,
                        "discovery.trending_score": max(
                            float((doc.get("discovery") or {}).get("trending_score") or 0),
                            20_000_000,
                        ),
                        "artist.name": target.artist.split("&")[0].strip(),
                    }
                },
            )
            await _clear_other_liked_bindings(db, target, doc["_id"])
        else:
            title = hit.get("title") or target.title
            uploader = (hit.get("artist") or {}).get("name") or target.artist
            star = match_featured_artist(title, uploader)
            display_artist = star.name if star else target.artist.split("&")[0].strip()
            if star:
                apply_featured_discovery(hit, star)
            hit.setdefault("discovery", {})["liked_music_target"] = {
                "title": target.title,
                "artist": target.artist,
            }
            hit["discovery"]["playlist_liked_music"] = True
            hit["discovery"]["trending_score"] = max(
                float(hit.get("discovery", {}).get("trending_score") or 0),
                20_000_000,
            )

            artist_doc = await artists_repo.upsert_by_name(display_artist, genres=hit.get("genres"))
            hit["artist"] = {"id": artist_doc["_id"], "name": display_artist}

            existing = await find_existing_track(db, hit)
            if existing and hit.get("_id") is None:
                hit["_id"] = existing["_id"]
            doc, _created = await tracks_repo.upsert_track(hit)
            tid = str(doc["_id"])
        await _clear_other_liked_bindings(db, target, doc["_id"])
        playlist_track_ids.append(tid)
        prov = (doc.get("source") or {}).get("provider")
        row.update(
            {
                "matched": True,
                "track_id": tid,
                "provider": prov,
                "preview_only": bool((doc.get("playback") or {}).get("preview_only")),
                "catalog_title": doc.get("title"),
                "catalog_artist": (doc.get("artist") or {}).get("name"),
            }
        )
        results.append(row)
        print(f"OK   {target.artist} — {target.title}", file=sys.stderr, flush=True)

    return playlist_track_ids, results


async def _save_playlist(db, parts_map: dict[str, list[str]]) -> None:
    merged_ids: list[str] = []
    seen: set[str] = set()
    for p in sorted(parts_map.keys(), key=int):
        for tid in parts_map[p]:
            if tid not in seen:
                seen.add(tid)
                merged_ids.append(tid)

    await db.playlists.update_one(
        {"slug": PLAYLIST_ID},
        {
            "$set": {
                "slug": PLAYLIST_ID,
                "title": PLAYLIST_TITLE,
                "description": PLAYLIST_DESCRIPTION,
                "parts": parts_map,
                "track_ids": merged_ids,
                "updated_at": utcnow(),
            },
            "$setOnInsert": {"created_at": utcnow(), "source": "liked_music_import"},
        },
        upsert=True,
    )


async def main() -> None:
    settings = get_settings()
    if not await connect_mongodb(settings.mongodb_uri, settings.mongodb_database):
        raise SystemExit("MongoDB unavailable")

    db = get_catalog_db()
    assert db is not None
    await ensure_catalog_indexes(db)
    audius = AudiusCatalogProvider()
    jamendo = JamendoCatalogProvider()
    deezer = DeezerCatalogProvider()
    tracks_repo = TrackRepository(db)
    artists_repo = ArtistRepository(db)
    only_misses = os.environ.get("LIKED_MUSIC_ONLY_MISSES", "").strip() in ("1", "true", "yes")
    quality_pass = os.environ.get("LIKED_MUSIC_QUALITY_PASS", "").strip() in ("1", "true", "yes")
    if quality_pass:
        only_misses = False

    import_all = os.environ.get("LIKED_MUSIC_ALL", "").strip() in ("1", "true", "yes")
    if import_all:
        parts = sorted(LIKED_MUSIC_PARTS.keys())
    else:
        parts = [int(os.environ.get("LIKED_MUSIC_PART", "1"))]

    existing = await db.playlists.find_one({"slug": PLAYLIST_ID}) or {}
    parts_map: dict[str, list[str]] = dict(existing.get("parts") or {})
    all_results: list[dict] = []

    for part in parts:
        print(f"=== part {part} ===", file=sys.stderr, flush=True)
        ids, results = await _import_part(
            part,
            audius=audius,
            jamendo=jamendo,
            deezer=deezer,
            db=db,
            artists_repo=artists_repo,
            tracks_repo=tracks_repo,
            only_misses=only_misses,
            quality_pass=quality_pass,
        )
        parts_map[str(part)] = ids
        all_results.extend(results)
        await _save_playlist(db, parts_map)

    matched = sum(1 for r in all_results if r.get("matched"))
    print(
        json.dumps(
            {
                "parts": parts,
                "playlist": PLAYLIST_ID,
                "targets": len(all_results),
                "matched": matched,
                "missing": len(all_results) - matched,
                "playlist_tracks": len(
                    {tid for ids in parts_map.values() for tid in ids}
                ),
                "tracks": all_results,
            },
            indent=2,
        )
    )
    await close_mongodb()


if __name__ == "__main__":
    asyncio.run(main())
