-- GreenTube Music initial schema (PostgreSQL)
-- Apply with: psql $DATABASE_URL -f infra/schema.sql
-- Or use Alembic once migrations are wired.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY,
  email VARCHAR(320) UNIQUE NOT NULL,
  display_name VARCHAR(120) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_preferences (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  discovery_bias DOUBLE PRECISION NOT NULL DEFAULT 0.5,
  explicit_genres TEXT[],
  extras JSONB
);

CREATE TABLE IF NOT EXISTS artists (
  id UUID PRIMARY KEY,
  name VARCHAR(512) NOT NULL,
  musicbrainz_id VARCHAR(64) UNIQUE,
  image_url TEXT
);
CREATE INDEX IF NOT EXISTS idx_artists_name_trgm ON artists USING gin (name gin_trgm_ops);

CREATE TABLE IF NOT EXISTS albums (
  id UUID PRIMARY KEY,
  title VARCHAR(512) NOT NULL,
  artist_id UUID REFERENCES artists(id),
  release_date VARCHAR(32),
  musicbrainz_id VARCHAR(64) UNIQUE,
  artwork_url TEXT
);
CREATE INDEX IF NOT EXISTS idx_albums_title_trgm ON albums USING gin (title gin_trgm_ops);

CREATE TABLE IF NOT EXISTS tracks (
  id UUID PRIMARY KEY,
  title VARCHAR(512) NOT NULL,
  album_id UUID REFERENCES albums(id),
  duration_ms INTEGER NOT NULL DEFAULT 0,
  isrc VARCHAR(32),
  musicbrainz_id VARCHAR(64) UNIQUE,
  artwork_url TEXT,
  genres TEXT[]
);
CREATE INDEX IF NOT EXISTS idx_tracks_title_trgm ON tracks USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_tracks_isrc ON tracks(isrc);

CREATE TABLE IF NOT EXISTS track_providers (
  id UUID PRIMARY KEY,
  track_id UUID NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
  provider VARCHAR(64) NOT NULL,
  provider_track_id VARCHAR(255) NOT NULL,
  playback_type VARCHAR(64) NOT NULL DEFAULT 'stream',
  availability VARCHAR(32) NOT NULL DEFAULT 'available',
  territory VARCHAR(8),
  stream_url TEXT,
  UNIQUE (provider, provider_track_id)
);
CREATE INDEX IF NOT EXISTS idx_track_providers_track ON track_providers(track_id);

CREATE TABLE IF NOT EXISTS playlists (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  is_public BOOLEAN NOT NULL DEFAULT FALSE,
  collaborative BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS playlist_tracks (
  id UUID PRIMARY KEY,
  playlist_id UUID NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
  track_id UUID NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  added_by UUID REFERENCES users(id),
  added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (playlist_id, position)
);

CREATE TABLE IF NOT EXISTS likes (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  track_id UUID NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
  polarity INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, track_id)
);

CREATE TABLE IF NOT EXISTS play_events (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  track_id UUID NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
  event_type VARCHAR(32) NOT NULL,
  position_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_play_events_user_time ON play_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_play_events_type ON play_events(event_type);

CREATE TABLE IF NOT EXISTS listening_history (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  track_id UUID NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
  played_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_history_user_time ON listening_history(user_id, played_at DESC);

CREATE TABLE IF NOT EXISTS ingest_cursors (
  source VARCHAR(64) PRIMARY KEY,
  cursor_value TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
