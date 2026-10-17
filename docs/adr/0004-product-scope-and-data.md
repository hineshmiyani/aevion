# ADR-0004: Product scope: tracks, data, demo dataset and the five questions

**Status:** Accepted · **Date:** 2026-10-17 · **Decided by:** the team (Hinesh, Jignesh, Jaydeep, Het) · **Source:** [grilling round 1](../grilling/round-01.md), Q1–Q4

## Decision

| Topic | Decision |
|---|---|
| Tracks | **03 Company Brain** (main) + **01 Agents That Act** (triage agent). Track 02 is not claimed. |
| Data sources | **Public GitHub only:** issues, PRs, review comments, commits, CODEOWNERS, docs markdown, releases. No Discord or Slack. |
| Demo dataset | FalkorDB org, **9 repos**: FalkorDB, GraphRAG-SDK, QueryWeaver, code-graph, falkordb-browser, falkordb-py, falkordb-ts, FalkorDB-MCPServer, docs. **Last 12 months.** Bot accounts filtered out. |
| Generality | The ingester takes any public org and repo list; the FalkorDB set is configuration, not code. |
| Persona | Maintainer or new contributor at an open-source company. |
| The five questions | 1. Who knows X? 2. Why was X decided? 3. What's the history of X? 4. What else does this touch? 5. Catch me up on X since a date. |

**Scope rule:** nothing outside the five questions and the triage agent gets built until all five answer well in the demo.

## Why

- Claiming Track 02 with a thin memory story could make judges doubt the stronger claims.
- FalkorDB's Discord requires a login, so Rule 6 likely forbids it. GitHub alone covers "docs, tickets and chats" through markdown docs, issues, and comment threads, with one ingester.
- Pinning nine repos and 12 months keeps loading inside GitHub's API rate limits and the timeline, while still giving deep expertise and decision history.

## Consequences

- The ingester must handle cross-repo references (`FalkorDB/GraphRAG-SDK#12`), renamed users, and bot detection.
- "Chats" in our pitch means discussion threads on PRs and issues. Say this explicitly in the README so judges don't look for Slack.
