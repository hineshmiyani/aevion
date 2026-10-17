# ADR-0013: Triage never pings real people

**Status:** Accepted · **Date:** 2026-10-17 · **Decided by:** Hinesh Miyani · **Refines:** [ADR-0005](0005-triage-agent-writes-only-to-sandbox.md), SPEC `triage` ("otherwise mention them")

## Context

The triage Expert is computed from the **FalkorDB** graph, so it is a real FalkorDB maintainer. ADR-0005 keeps our writes on our own sandbox repo, but a GitHub comment there that says `@DvirDukhan` still sends that person a notification. They never agreed to take part in our demo.

## Decision

- The "mention" action names the Expert as a **profile link**, `[login](https://github.com/login)`, never `@login`.
- Any `@login` in the model's draft is rewritten to a profile link before the reply leaves `triage/service.py` (`defuse_mentions`).
- A bare `#123` in a draft is linked to the issue or PR we meant, or escaped (`\#123`), because on the sandbox it would autolink to the sandbox's own issue 123.
- "Assign" applies only to collaborators on the sandbox repo, which GitHub enforces anyway.

## Consequences

- The demo still shows *who* to ask, with a working link, without notifying anyone.
- The rule lives in code with tests, not only in the prompt, so a model that ignores the prompt can't break it.
