# ADR-0005: The triage agent writes only to our sandbox repo

**Status:** Accepted · **Date:** 2026-10-17 · **Decided by:** the team (Hinesh, Jignesh, Jaydeep, Het) · **Source:** [grilling round 1](../grilling/round-01.md), Q5

## Decision

The Track 01 triage agent, for a new issue:

1. finds duplicates and related issues,
2. works out which component it touches,
3. picks the best owner from the expertise graph,
4. drafts a reply,
5. **applies labels, assigns the owner and posts the comment.**

Step 5 runs **only on a sandbox repo we own**, seeded with copies of real issues. On FalkorDB's repositories the agent is read-only and shows "here's what I would do" with the same reasoning path.

## Why

Posting automated comments on FalkorDB's real repos during the hackathon would look like spam, could break the rules, and is outside what our GitHub token should be allowed to do. A sandbox still gives a genuine "agent acts" demo for Track 01.

## Consequences

- Write actions are behind an explicit allow-list of repositories in configuration. Any write to a repo outside the list fails, not just warns.
- We need a sandbox repo, a seeding script, and a GitHub token scoped to that repo for writes (round 2 picks names and ownership).
- The demo shows both modes: a dry-run on a real FalkorDB issue, and a live action on the sandbox.
