"""Runtime settings, read from the environment (and `.env` in development)."""

import shutil
import subprocess
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(REPO_ROOT / ".env", ".env"), extra="ignore")

    falkordb_url: str = "redis://localhost:6379"
    # Read-only token for public GitHub data. Falls back to `gh auth token` in development.
    github_token: str | None = None
    raw_cache_dir: Path = REPO_ROOT / "data" / "raw"

    def resolved_github_token(self) -> str:
        if self.github_token:
            return self.github_token
        gh = shutil.which("gh")
        if gh:
            result = subprocess.run([gh, "auth", "token"], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        raise RuntimeError(
            "Set GITHUB_TOKEN (or log in with `gh auth login`) to ingest GitHub data"
        )
