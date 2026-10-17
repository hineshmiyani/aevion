"""Per-org ingestion config, read from config/orgs/<org>.toml."""

import tomllib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path


@dataclass(frozen=True)
class RepoConfig:
    name: str
    component_depth: int
    depth_overrides: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class OrgConfig:
    org: str
    since_months: int
    repos: tuple[RepoConfig, ...]
    bot_logins: frozenset[str]

    def since(self, now: datetime | None = None) -> datetime:
        """Start of the ingestion window, truncated to midnight UTC so it is stable within a
        day (raw-cache keys include it)."""
        start = (now or datetime.now(UTC)) - timedelta(days=30 * self.since_months)
        return start.replace(hour=0, minute=0, second=0, microsecond=0)

    def repo(self, name: str) -> RepoConfig:
        for repo in self.repos:
            if repo.name.lower() == name.lower():
                return repo
        raise KeyError(f"{name!r} is not configured for {self.org}")


def load_org_config(path: Path) -> OrgConfig:
    data = tomllib.loads(path.read_text())
    default_depth = int(data.get("component_depth", 2))
    return OrgConfig(
        org=data["org"],
        since_months=int(data.get("since_months", 12)),
        repos=tuple(
            RepoConfig(
                name=r["name"],
                component_depth=int(r.get("component_depth", default_depth)),
                depth_overrides={
                    k: int(v) for k, v in r.get("component_depth_overrides", {}).items()
                },
            )
            for r in data["repos"]
        ),
        bot_logins=frozenset(login.lower() for login in data.get("bot_logins", [])),
    )
