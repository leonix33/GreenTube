from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    port: int = 8000
    environment: str = "development"
    frontend_url: str = "http://localhost:3000"
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = "postgresql+asyncpg://greentube:greentube@localhost:5432/greentube"
    redis_url: str = "redis://localhost:6379/0"
    mongodb_uri: str = ""
    mongodb_database: str = "greentube"
    auto_seed_mongo: bool = True
    jamendo_client_id: str = ""
    admin_api_key: str = ""
    musicbrainz_user_agent: str = "GreenTubeMusic/0.1.0 (dev@localhost)"
    # When false, playback never falls back to Deezer 30s previews (full streams only).
    allow_preview_playback: bool = False  # env: ALLOW_PREVIEW_PLAYBACK
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://localhost:8000/api/integrations/spotify/callback"
    # Optional — attach official YouTube music videos via Data API (embed playback only).
    youtube_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
