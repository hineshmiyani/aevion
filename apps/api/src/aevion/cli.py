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
from aevion.ingest.loader import (
    graph_counts,
    link_references,
    prune_orphan_components,
    unlink_file_components,
)
from aevion.ingest.org_config import load_org_config
from aevion.ingest.pipeline import ingest_repo

DEFAULT_ORG_CONFIG = REPO_ROOT / "config" / "orgs" / "falkordb.toml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aevion")
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="Load GitHub data into the org graph")
    ingest.add_argument("--org-config", type=Path, default=DEFAULT_ORG_CONFIG)
    ingest.add_argument("--repos", nargs="*", help="Subset of configured repos (default: all)")
    ingest.add_argument("--cache", action="store_true", help="Reuse raw GitHub responses")
    ingest.add_argument(
        "--reset-components",
        action="store_true",
        help="Rebuild File→Component links (after changing component depth in the config)",
    )

    args = parser.parse_args(argv)
    if args.command == "ingest":
        return _ingest(args.org_config, args.repos, args.cache, args.reset_components)
    return 1


def _ingest(
    org_config_path: Path, repos: list[str] | None, use_cache: bool, reset_components: bool
) -> int:
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
            full_name = f"{config.org}/{config.repo(name).name}"
            if reset_components:
                unlink_file_components(graph, full_name)
            report = ingest_repo(graph, client, config, name)
            if reset_components:
                pruned = prune_orphan_components(graph, full_name)
                print(f"{full_name}: pruned {pruned} stale components")
            print(
                f"{report.repo}: {report.pull_requests} PRs, {report.issues} issues, "
                f"{report.comments} comments, {report.file_changes} file changes, "
                f"{report.releases} releases, {report.ownerships} ownerships"
            )
        link_references(graph)
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
