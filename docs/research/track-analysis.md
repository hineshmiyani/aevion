# Track analysis: why Company Brain

**Date:** 2026-10-17 · **Outcome:** [ADR-0001](../adr/0001-company-brain-direction.md)

We compared concrete product ideas across all three tracks, judging them the way a FalkorDB judge skimming thousands of entries would.

## What we think judges reward

WeMakeDevs runs hackathons as go-to-market for the sponsor, so judges favour the project FalkorDB would be proudest to show. With ~7,400 registrants, each entry gets a short look, mostly the video and README. What survives that look:

1. **Obviously real within 30 seconds:** real data, a live deployment, a polished UI.
2. **The graph is visibly essential:** every answer shows the path that produced it.
3. **Several FalkorDB features in one product:** Cypher paths, built-in algorithms, MCP, separate graphs for each tenant.
4. **A team that can defend the graph model** when questioned.

## Candidate ideas

### Track 01: Agents That Act on Connected Data

| Idea | Summary | Verdict |
|---|---|---|
| 1A Attack Path Agent | Infrastructure + CVE graph; finds paths from the internet to sensitive data; ranks vulnerabilities by reachability; opens fix tickets | Strong, but the infrastructure must be synthetic, which reads as a toy |
| 1B Supply-Chain Blast Radius | npm/PyPI dependency graph + maintainers + vulnerabilities; "if this package were compromised, who's affected?" | Strong, but heavy data loading |
| 1C Fraud Ring Investigator | Community detection on transaction data | Crowded: expect dozens of these |
| 1D Codebase impact agent | "What breaks if I change X" | FalkorDB already ships `code-graph`, so we'd be compared to the sponsor's own tool |

### Track 02: Agent Memory and Coordination

| Idea | Summary | Verdict |
|---|---|---|
| 2A Shared memory for coding agents (MCP) | Memory shared across Claude Code, Cursor and others | Crowded by mem0, Zep and Graphiti (which already runs on FalkorDB) |
| 2B Multi-agent support desk | Separate memory per customer, handoffs between agents | Covers every focus point but looks like an ordinary enterprise demo |
| 2C Agent-swarm blackboard | Many agents claiming tasks and posting evidence on one shared graph | Impressive concurrency, but the use case is unclear |

### Track 03: Company Brain

| Idea | Summary | Verdict |
|---|---|---|
| **3 Company Brain of a real OSS org** | Public GitHub issues, PRs, reviews, commits and docs → expertise, decision trails, live updates, triage actions | **Chosen** |

## Scoring

| Idea | Graph is essential | Demo strength | Crowding | Shippable by deadline | Data |
|---|---|---|---|---|---|
| **3 Company Brain (FalkorDB org)** | High | High (the judges' own org) | Medium | Medium | Real, public |
| 1A Attack Path | Very high | High | Low | Medium | Synthetic + public CVEs |
| 1B Supply-Chain | Very high | High | Low | Medium-hard | Real, public |
| 1C Fraud Rings | High | Medium | Very high | Easy | Public |
| 2A Coding-agent memory | Medium-high | High if done well | High | Medium | Our own |
| 2B Support desk | Medium | Low | Medium | Easy | Synthetic |
| 2C Swarm | High | Medium | Low | Hard | Synthetic |

## Why Company Brain wins

- **Judges can verify the answers themselves.** Pointed at FalkorDB's own org, a correct "who knows the query planner?" is instantly convincing to a FalkorDB engineer. Synthetic data can't produce that reaction.
- **It covers two tracks honestly.** The triage agent that acts on the graph gives a genuine Track 01 entry.
- **It shows off the most FalkorDB features:** path queries for decision trails, PageRank and centrality for expertise, community detection for discovering teams, MCP, separate graphs for each org.
- **Low risk of getting the domain wrong:** every teammate lives in GitHub daily.

**Main risk:** a wrong answer about the judges' own org is just as visible as a right one. Mitigation: always show the evidence path, never a bare claim.

## Facts gathered (2026-10-17)

- FalkorDB org: ~4,300 issues and ~10,600 PRs total; ~2,400 PRs merged in the last 6 months.
- Largest active repos: FalkorDB (10k★), QueryWeaver, GraphRAG-SDK, code-graph, falkordb-browser, falkordb-py, falkordb-ts, FalkorDB-MCPServer, docs.
- FalkorDB already ships its own MCP server, `text-to-cypher`, `code-graph` and `QueryWeaver`. Build alongside these tools rather than competing with them.
