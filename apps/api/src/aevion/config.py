"""Runtime settings, read from the environment (and `.env` in development)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    falkordb_url: str = "redis://localhost:6379"
