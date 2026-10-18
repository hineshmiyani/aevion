# ADR-0013: Nothing we post pings people or references FalkorDB's issues

**Status:** Accepted · **Date:** 2026-10-17 · **Decided by:** Hinesh Miyani · **Refines:** [ADR-0005](0005-triage-agent-writes-only-to-sandbox.md), SPEC `triage` ("otherwise mention them")

## Context

The triage Expert is computed from the **FalkorDB** graph, so it is a real FalkorDB maintainer. ADR-0005 keeps our writes on our own sandbox repo, but a GitHub comment there that says `@DvirDukhan` still sends that person a notification. They never agreed to take part in our demo.

A second leak has the same shape. When a public issue or comment references another repo's issue or PR (`FalkorDB/FalkorDB#123`, or its URL), GitHub adds a "mentioned this issue" event to **that** issue's timeline. Seeding 30 copies that link to their originals, or posting triage replies that link to similar issues, would leave visible traces on FalkorDB's repos.

## Decision

- The "mention" action names the Expert as a **profile link**, `[login](https://github.com/login)`, never `@login`.
- Any `@login` in the model's draft is rewritten to a profile link before the reply leaves `triage/service.py` (`defuse_mentions`).
- A bare `#123` in a draft is linked to the issue or PR we meant, or escaped (`\#123`), because on the sandbox it would autolink to the sandbox's own issue 123.
- "Assign" applies only to collaborators on the sandbox repo, which GitHub enforces anyway.
- Everything posted on the sandbox (seeded copies, triage replies) writes references to other repos' issues and PRs as **code spans**, which GitHub doesn't turn into references (`sandbox/safety.py`, `inert_references`). Text copied from an issue has its bare `#123` qualified with the original repo first, so it can be made inert too. Clickable links to FalkorDB stay in Aevion's own UI.
- The seeded copies name their original in code (`FalkorDB/FalkorDB#3357` and its URL), and their hidden marker spells the key without `#`.

- Before posting, the apply step re-scans the final comment (`foreign_references`). If anything outside code could still notify someone or reference another repo, the comment is not posted and the action is marked failed. This caught nothing in production, but the first version of the link rule had a gap (link text in code split the link in two), so the rule is not trusted alone.

## Consequences

- The demo still shows *who* to ask, with a working link, without notifying anyone.
- The rules live in code with tests, not only in the prompt, so a model that ignores the prompt can't break it.
