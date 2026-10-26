"""Application configuration loaded from environment variables (and an optional .env file)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development")
    app_name: str = Field(default="IIT Ropar Facility Booking")

    # SQLAlchemy URL. Format: postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE
    database_url: str = Field(default="postgresql+psycopg://postgres:postgres@localhost:5432/facility_booking")
    # Separate database used by pytest. Its name must end in "_test" (tests wipe it).
    test_database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/facility_booking_test"
    )
    # Seconds to wait for PostgreSQL before reporting it as unreachable.
    database_connect_timeout: int = Field(default=5, ge=1)

    # Comma-separated list of browser origins allowed to call the API.
    frontend_url: str = Field(default="http://localhost:5173")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_url.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
