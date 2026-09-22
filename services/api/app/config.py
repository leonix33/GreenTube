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
    musicbrainz_user_agent: str = "GreenTubeMusic/0.1.0 (dev@localhost)"


@lru_cache
def get_settings() -> Settings:
    return Settings()
