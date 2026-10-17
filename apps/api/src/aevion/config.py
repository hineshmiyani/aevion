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

    # LLM via OpenRouter (ADR-0009). Model IDs are config, chosen by the bake-off (ADR-0010);
    # these defaults are the cheap development models.
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    agent_model: str = "anthropic/claude-haiku-5.5"
    extraction_model: str = "anthropic/claude-haiku-5.5"
    llm_budget_usd: float = 12.0  # hard stop; the OpenRouter key has its own credit limit too
    llm_data_dir: Path = REPO_ROOT / "data" / "llm"

    # ADR-0005: the only repos triage may write to. Everything else gets a dry run.
    triage_apply_repos: frozenset[str] = frozenset({"hineshmiyani/aevion-sandbox"})
    sandbox_repo: str = "hineshmiyani/aevion-sandbox"
    # Fine-grained token that GitHub limits to the sandbox repo (issues read/write only).
    sandbox_github_token: str | None = None
    # Shared with the sandbox repo's webhook settings; signs every delivery (HMAC SHA-256).
    github_webhook_secret: str | None = None
    # Repo whose code a freshly typed sandbox issue is triaged against (copies use their own).
    sandbox_default_repo: str = "FalkorDB/FalkorDB"

    # Browser origins allowed to call the API directly (the Vercel app, plus local dev).
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    # Shared with the Next.js proxy, which forwards each visitor's IP for rate limiting.
    proxy_secret: str | None = None

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
