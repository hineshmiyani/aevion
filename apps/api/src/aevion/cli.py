"""`aevion` command line: bootstrap and ingest org graphs."""

import argparse
import sys
import time
from pathlib import Path

from aevion.config import REPO_ROOT, Settings
from aevion.extract.run import dry_run, run_extraction
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
from aevion.llm.factory import ledger_for, llm_client

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

    extract = commands.add_parser("extract", help="Extract Decisions from PR and issue threads")
    extract.add_argument("--org", default="FalkorDB")
    extract.add_argument("--repo", help="Only this repo, e.g. FalkorDB/GraphRAG-SDK")
    extract.add_argument("--limit", type=int, help="At most this many threads (newest first)")
    extract.add_argument("--dry-run", action="store_true", help="Price the run; call no model")
    extract.add_argument("--max-usd", type=float, default=1.0, help="Refuse runs priced above this")
    extract.add_argument("--workers", type=int, default=8)

    commands.add_parser("cost", help="Show LLM spend from the ledger")
    check = commands.add_parser("llm-check", help="Make one tiny live LLM call and print its cost")
    check.add_argument("--model", help="Model ID (default: AGENT_MODEL)")

    args = parser.parse_args(argv)
    if args.command == "extract":
        return _extract(args)
    if args.command == "cost":
        return _cost()
    if args.command == "llm-check":
        return _llm_check(args.model)
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


def _extract(args: argparse.Namespace) -> int:
    settings = Settings()
    graph = OrgGraph(connect(settings), graph_name_for(args.org))
    model = settings.extraction_model
    priced = dry_run(graph, model, settings.openrouter_base_url, args.repo, args.limit)
    cost = "unknown" if priced.usd is None else f"${priced.usd:.4f}"
    print(
        f"{priced.threads} candidate threads, ~{priced.input_tokens:,} input + "
        f"~{priced.output_tokens:,} output tokens with {model}: projected {cost}"
    )
    if args.dry_run:
        return 0
    # SPEC boundary: any single LLM run projected over $1 needs a human decision first.
    if priced.usd is None or priced.usd > args.max_usd:
        print(f"Refusing: projected cost is above --max-usd {args.max_usd} (or unknown).")
        return 2
    report = run_extraction(graph, llm_client(settings), model, args.repo, args.limit, args.workers)
    print(
        f"{report.threads} threads → {report.decisions} decisions "
        f"({report.dropped_low_confidence} low-confidence dropped, {report.invalid_json} bad JSON, "
        f"{len(report.errors)} errors{', stopped on budget' if report.stopped_on_budget else ''})"
    )
    for error in report.errors[:5]:
        print("  error:", error)
    return 0


def _cost() -> int:
    settings = Settings()
    entries = ledger_for(settings).entries()
    by_model: dict[str, list[float]] = {}
    for e in entries:
        totals = by_model.setdefault(e["model"], [0, 0, 0.0])
        totals[0] += 1
        totals[1] += int(e["cached"])
        totals[2] += e["cost_usd"]
    for model, (calls, cached, usd) in sorted(by_model.items()):
        print(f"{model:40} {int(calls):5} calls ({int(cached)} cached)  ${usd:.4f}")
    total = sum(e["cost_usd"] for e in entries)
    print(
        f"{'total':40} {len(entries):5} calls  ${total:.4f}"
        f" of ${settings.llm_budget_usd:.2f} budget"
    )
    return 0


def _llm_check(model: str | None) -> int:
    settings = Settings()
    client = llm_client(settings)
    chosen = model or settings.agent_model
    result = client.chat(
        chosen,
        [{"role": "user", "content": "Reply with the single word: ready"}],
        max_tokens=10,
        purpose="llm-check",
    )
    print(
        f"{result.model}: {result.content.strip()!r}  cost ${result.usage.cost_usd:.6f}"
        f"{' (cached)' if result.cached else ''}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
