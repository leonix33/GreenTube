# GreenTube Catalog Architecture

## 1. Where catalog data comes from

| Provider | Role | Playable in GreenTube |
|----------|------|------------------------|
| **local** | Original demo WAV catalog (`catalog_seed.py`) | Yes |
| **jamendo** | Licensed/open streaming via official Jamendo API | Yes, when `audio` URL present |
| **audius** | Remote stream via Audius discovery API | Yes (stream URL only; no file copy) |
| **deezer** | Official Deezer search API | Yes — **30s preview** clips only (`playback.preview_only`) |
| **musicbrainz** | Official MusicBrainz REST metadata | No (metadata-only until matched) |

GreenTube does **not** scrape YouTube, Spotify, Apple Music, or rip third-party streams.

## 2. Metadata vs playable audio

- **Metadata** (title, artist, MBID, ISRC, artwork) can exist with `playback.available=false`.
- **Playable** tracks require `playback.available=true` and a legitimate `stream_url` (local static file or provider stream URL).
- Public list/search/home/genre endpoints prefer playable tracks for playback UX.

## 3. MongoDB collections

Primary database: `MONGODB_DATABASE` (default `greentube`).

- `tracks` — canonical catalog documents
- `artists`
- `albums`
- `genres` — browse taxonomy + cached counts
- `playback_sources` — provider stream map (unique on provider + provider_track_id)
- `catalog_imports` — import run audit log
- `playlists`, `users`, `likes`, `listening_history` — reserved for later phases (Postgres still used for auth today)

## 4. Provider architecture

```
services/api/app/providers/
  base.py          CatalogProvider interface
  local.py         Demo WAV catalog
  musicbrainz.py   Metadata-only
  jamendo.py       Optional streaming
  audius.py        Optional streaming
```

Ingestion: `app/catalog/ingestion.py` → normalize → dedupe → upsert artist/album/track.

## 5. Ingestion flow

```
Provider.fetch → normalize → validate → dedupe → upsert artist/album/track → playback_sources → MongoDB
```

Admin endpoints (require `X-Admin-Key` header):

- `POST /api/admin/catalog/import/local`
- `POST /api/admin/catalog/import/jamendo`
- `POST /api/admin/catalog/import/audius`
- `POST /api/admin/catalog/import/musicbrainz`
- `GET /api/admin/catalog/stats`

## 6. Deduplication order

1. ISRC
2. `source.provider` + `source.provider_track_id` (unique index)
3. MusicBrainz recording ID
4. Fingerprint: normalized artist + title + duration

## 7. Environment variables

```bash
MONGODB_URI=
MONGODB_DATABASE=greentube
AUTO_SEED_MONGO=true
JAMENDO_CLIENT_ID=
MUSICBRAINZ_USER_AGENT=GreenTubeMusic/0.1.0 (contact@yourdomain)
ADMIN_API_KEY=
```

Never commit real credentials.

## 8. Import music locally

```bash
cd services/api
cp ../../.env.example .env   # fill MONGODB_URI + ADMIN_API_KEY
pip install -r requirements.txt
PYTHONPATH=. python scripts/seed_mongo_catalog.py
uvicorn app.main:app --reload
```

Example Jamendo import:

```bash
curl -X POST "http://localhost:8000/api/admin/catalog/import/jamendo?genre=rock&limit=50" \
  -H "X-Admin-Key: $ADMIN_API_KEY"
```

## 9. Adding another provider

1. Create `app/providers/yourprovider.py` implementing `CatalogProvider`.
2. Map API responses to normalized track documents (`playback.available` rules).
3. Register admin import route in `app/routers/admin_catalog.py`.
4. Extend dedupe identifiers if the provider exposes ISRC/MBID.

## 10. Licensing limitations

- **MusicBrainz**: metadata only; follow rate limits and User-Agent policy.
- **Jamendo**: obey API terms; respect `audiodownload_allowed`; no download UI when false.
- **Audius**: use documented stream endpoints; do not mirror audio into GreenTube storage.
- **Deezer**: use public search + `preview` URLs only unless you have a full streaming partnership.
- **Local demo WAV**: generated original tones for development.

## Fallback behavior

If MongoDB is unreachable, public catalog endpoints fall back to in-memory `catalog_seed.py` so the app stays playable in dev.
