# ADR-0006: Keeping the graph current: polling, sandbox webhooks, time ranges

**Status:** Accepted · **Date:** 2026-10-17 · **Decided by:** the team (Hinesh, Jignesh, Jaydeep, Het) · **Source:** [grilling round 1](../grilling/round-01.md), Q6

## Decision

- **FalkorDB's org:** poll GitHub every few minutes for changes. Use conditional requests (ETags / `since` timestamps) so unchanged data costs nothing against the rate limit.
- **Our sandbox repo:** real GitHub webhooks, so the live demo shows an issue filed → graph updated within seconds → agent triages it.
- **History is kept, not overwritten:** facts that change (an owner, a decision, a status) get validity time ranges, and superseded facts stay queryable.

## Why

We can't install webhooks on an org we don't own. Polling covers the real org; webhooks give the sandbox demo a "live" moment. Time ranges serve Track 03's "keeping knowledge current" focus and let us answer "what did we believe before this changed?"

## Consequences

- Ingestion must be idempotent (MERGE on stable GitHub IDs), because polling will see the same objects repeatedly.
- The graph model needs `valid_from` / `valid_to` (or equivalent) on changeable relationships; round 2 defines exactly which.
- The webhook endpoint must be publicly reachable for the demo, which ties into the deployment decision in round 2.
