# ADR-0011: Graph data model

**Status:** Accepted · **Date:** 2026-10-17 · **Decided by:** the team (Hinesh, Jignesh, Jaydeep, Het) · **Source:** [grilling round 2](../grilling/round-02.md), Q1–Q6 · **Detail:** [graph-model.md](../architecture/graph-model.md)

## Decision

1. **Components come from paths and labels.** A Component is a directory prefix in a repo (for example `FalkorDB/FalkorDB:src/execution_plan`), and GitHub labels map onto Components. Built deterministically, with no LLM.
2. **Comments are nodes.** `(:Comment {excerpt, url, created_at})`, so evidence paths can cite the exact comment a decision or expertise signal came from.
3. **Expertise is computed live in Cypher** at question time: weighted traversal over authored and reviewed merged PRs, fixes and comments in the Component, with recency decay. No precomputed expertise edges.
4. **Decisions come from filtered LLM extraction.** A cheap deterministic filter picks candidate threads (merged PRs with 3+ review comments or a linked issue; closed issues with 3+ comments; docs changes). The extraction model ([ADR-0010](0010-llm-model-bake-off.md)) produces `Decision {summary, rationale, alternatives, decided_at, confidence}` linked to its thread, evidence comments, people and components.
5. **One FalkorDB graph per org** (multigraph): `org:FalkorDB` for the real org, `org:aevion-sandbox` for the triage demo.
6. **Minimal time model.** `OWNS` edges (from CODEOWNERS history) carry `valid_from` / `valid_to`; Decisions link through `SUPERSEDES`. Issue and PR state changes are timestamp properties. All times are stored as **epoch milliseconds** (integers) for simple arithmetic in Cypher.

## Why

- Paths and labels match how maintainers think about a codebase, and cost nothing to build.
- Answering expertise with a live traversal is the clearest proof for Rule 3: the answer *is* the graph query, and its evidence path comes out of the same query.
- Filtering before extraction keeps the LLM budget small (ADR-0009) and the Decision set high-signal.
- One graph per org uses a FalkorDB feature named on the hackathon page and keeps sandbox writes out of real data.

## Consequences

- Ingestion MERGEs on stable keys (GitHub IDs, `repo#number`, login), so polling is idempotent.
- Component granularity (how many directory levels) needs a per-repo config; default is 2 levels.
- Expertise weights and decay are tunable constants. They belong in the Cypher query reference and must be explainable to judges.
- Duplicate detection for triage is still open (full-text vs vectors), deferred to round 3.
