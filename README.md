# GreenTube Music

Independent music streaming platform: YouTube Music–style experience, owned recommendation engine, open/user-owned/licensed audio providers.

## Architecture

```text
apps/web                 Next.js PWA (React + TypeScript + Tailwind)
services/api             FastAPI catalog, auth, playlists, playback
services/recommendations FastAPI recommendation / mixes / radio
services/ingestion       Catalog ingest (MusicBrainz, Cover Art, providers)
infra                    Render, Docker, env templates
```

**Catalog ≠ audio.** Metadata is canonical; playback resolves through `TrackProvider` adapters (open, user-owned, licensed). No unofficial scraping of commercial streams.

## Quick start

### API

```bash
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Web

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Implementation order

1. Web shell + player UI  
2. Auth  
3. Database schema  
4. Catalog ingestion  
5. Search  
6. Player + providers  
7. Playlists / library  
8. Recommendations  
9. PWA / offline  

## License

Proprietary — all rights reserved.
