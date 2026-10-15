"""Application configuration loaded from environment variables (and an optional .env file)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development")
    app_name: str = Field(default="IIT Ropar Facility Booking")

    mongodb_uri: str = Field(default="mongodb://localhost:27017")
    mongodb_database: str = Field(default="facility_booking")
    # Fail fast when MongoDB is unreachable instead of hanging for pymongo's 30 s default.
    mongodb_server_selection_timeout_ms: int = Field(default=5000, ge=100)

    # Comma-separated list of browser origins allowed to call the API.
    frontend_url: str = Field(default="http://localhost:5173")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_url.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
