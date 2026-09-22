# GreenTube Music Architecture

## Product

Streaming UX similar to modern music apps, with an **independent catalog**, **owned recommendations**, and **legitimate audio providers** (open / user-owned / licensed). No unofficial re-streaming of commercial catalogs.

## Component map (from Remotely Match)

| Remotely Match | GreenTube |
|---|---|
| Vue 3 PWA | Next.js PWA (`apps/web`) |
| Node/Express | FastAPI (`services/api`) |
| Job matching | Recommendations (`services/recommendations`) |
| Job agent / SQLite | Ingestion workers (`services/ingestion`) |
| MongoDB Atlas | PostgreSQL (`infra/schema.sql`) |
| Docker + Render | `infra/docker/*` + `infra/render.yaml` |

## Provider model

```text
Track (canonical) → TrackProvider[] → open | user_owned | licensed SDK
```

`GET /api/tracks/{id}/stream` resolves the best available provider.

## Local development

1. Postgres + Redis running locally (or skip DB for `/health` only).
2. `services/api`: `uvicorn app.main:app --reload`
3. `apps/web`: `npm run dev`
4. Optional: recommendations service on `:8001`

## Next build steps

Auth UI → apply schema → MusicBrainz normalize/upsert → search UX → HTMLAudio / Media Session player → playlists → affinity recommender.
