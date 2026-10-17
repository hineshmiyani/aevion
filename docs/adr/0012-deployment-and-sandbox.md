# ADR-0012: Deployment on Railway + Vercel; sandbox repo `hineshmiyani/aevion-sandbox`

**Status:** Accepted · **Date:** 2026-10-17 · **Decided by:** the team (Hinesh, Jignesh, Jaydeep, Het) · **Source:** [grilling round 2](../grilling/round-02.md), Q7, Q8, Q12

## Decision

| Piece | Where |
|---|---|
| FalkorDB | Self-hosted `falkordb/falkordb` Docker image on **Railway**, with a persistent volume, reachable only on Railway's private network |
| FastAPI API (agent, tools, MCP, webhook endpoint) | **Railway** service |
| Polling worker | **Railway** service (same image, different command) |
| Next.js frontend | **Vercel** |
| Triage sandbox | Public repo **`hineshmiyani/aevion-sandbox`**, seeded with ~30 copied FalkorDB issues, each linking back to the original |

The agent writes to the sandbox using a **fine-grained GitHub token limited to that one repo** (issues and comments only), which enforces [ADR-0005](0005-triage-agent-writes-only-to-sandbox.md) at the credential level, not just in code.

## Why

- **FalkorDB Cloud's free tier** has no TLS, no continuous persistence and no backups, so the demo graph could vanish during judging. Self-hosting gives us persistence and memory control. Re-ingesting is cheap because LLM results are cached.
- **Railway** gives one private network for the database, API and worker, plus a public HTTPS URL for GitHub webhooks. **Vercel** is the fastest route to a polished frontend URL.
- A **sandbox under your account** needs no extra organisation setup, and a token scoped to one repo makes accidental writes to FalkorDB's repos impossible.

## Consequences

- Railway costs a small amount once the trial credit runs out. Check the account's remaining credit before deploying.
- FalkorDB is never exposed publicly; only the API is.
- Two GitHub tokens: a read-only one for ingestion (public data) and the sandbox-only write token.
- The sandbox repo is public. Seeded issues must say they are copies, with links to the originals, so no one mistakes them for real reports.
