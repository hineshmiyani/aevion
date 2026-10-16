# ADR-0001: Build a Company Brain from a public GitHub org

**Status:** Accepted · **Date:** 2026-10-17 · **Decided by:** Hinesh Miyani (team lead)

## Context

Graph Hacks has three tracks with separate prizes, and a team may enter several. We have about 1.5 days of build time and three people. The full comparison of seven candidate ideas is in [track-analysis.md](../research/track-analysis.md).

## Decision

Build a **Company Brain**: an agent that loads a public GitHub organisation into FalkorDB and answers questions about ownership, expertise and decisions, showing the graph path as evidence. The demo dataset is the **FalkorDB GitHub org**. Track 03 is the main track. Track 01 coverage, through a triage agent that acts on the graph, is proposed but not yet locked (see [grilling round 1](../grilling/round-01.md), Q1).

## Alternatives considered

- **Attack Path Agent (Track 01):** the graph is very essential and the field is less crowded, but the infrastructure must be synthetic and getting the security modelling right is risky in the time we have.
- **Supply-Chain Blast Radius (Track 01):** real data and timely, but loading dependency graphs at scale is a big job.
- **Track 02 ideas:** hard to demo in a short video, and crowded by existing memory products (mem0, Zep, Graphiti).

## Consequences

- The ingester must cope with real, messy GitHub data (bots, renamed users, cross-repo references).
- Answer quality is visible to judges who know the ground truth, so evidence paths are mandatory.
- We must not write to FalkorDB's repositories; any write action needs a sandbox repo we own.
