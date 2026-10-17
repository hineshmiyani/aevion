"""`aevion` command line: bootstrap and ingest org graphs."""

import argparse
import sys
import time
from pathlib import Path

from aevion.config import REPO_ROOT, Settings
from aevion.graph.client import OrgGraph, connect
from aevion.graph.naming import graph_name_for
from aevion.graph.schema import bootstrap
from aevion.ingest.github import GitHubClient
from aevion.ingest.loader import graph_counts
from aevion.ingest.org_config import load_org_config
from aevion.ingest.pipeline import ingest_pull_requests

DEFAULT_ORG_CONFIG = REPO_ROOT / "config" / "orgs" / "falkordb.toml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aevion")
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="Load GitHub data into the org graph")
    ingest.add_argument("--org-config", type=Path, default=DEFAULT_ORG_CONFIG)
    ingest.add_argument("--repos", nargs="*", help="Subset of configured repos (default: all)")
    ingest.add_argument("--cache", action="store_true", help="Reuse raw GitHub responses")

    args = parser.parse_args(argv)
    if args.command == "ingest":
        return _ingest(args.org_config, args.repos, args.cache)
    return 1


def _ingest(org_config_path: Path, repos: list[str] | None, use_cache: bool) -> int:
    settings = Settings()
    config = load_org_config(org_config_path)
    graph = OrgGraph(connect(settings), graph_name_for(config.org))
    bootstrap(graph)
    client = GitHubClient(
        settings.resolved_github_token(), settings.raw_cache_dir if use_cache else None
    )
    started = time.monotonic()
    before = graph_counts(graph)
    try:
        for name in repos or [r.name for r in config.repos]:
            report = ingest_pull_requests(graph, client, config, name)
            print(
                f"{report.repo}: {report.pull_requests} PRs, {report.people} people, "
                f"{report.file_changes} file changes"
            )
    finally:
        client.close()
    after = graph_counts(graph)
    print(
        f"{graph.name}: {after['nodes']} nodes (+{after['nodes'] - before['nodes']}), "
        f"{after['edges']} edges (+{after['edges'] - before['edges']}) "
        f"in {time.monotonic() - started:.1f}s"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
