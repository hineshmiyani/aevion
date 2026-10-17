# Implementation plan: Aevion

**Status:** v1, 2026-10-17 · **Task:** AEV-16 · **Implements:** [docs/product/SPEC.md](../docs/product/SPEC.md) (approved)

**Tasks are tracked in Notion: [Aevion Tasks](https://app.notion.com/p/374521bfeac54306bed66e0764812cda).** Each task there has acceptance criteria, a verification step, size, module, and **Blocked by / Blocks** links. This file holds the plan, order, checkpoints and risks. It is **not** a second checklist; tick tasks off in Notion.

## Overview

We build Aevion in thin vertical slices: real GitHub data → FalkorDB → a Cypher tool with an evidence path → HTTP → UI. Each slice leaves `develop` working. The highest-risk unknowns come first: whether FalkorDB supports the Cypher functions we rely on, and what real GitHub data looks like.

**Staffing:** the four of us (Hinesh, Jignesh, Jaydeep, Het) split the tasks, and each task's owner is set in Notion. Every task is self-contained and marked parallel-safe where it is, so we can build in parallel.

## Architecture decisions this plan relies on

- One graph per org; MERGE on stable keys, so ingestion can always be re-run safely ([ADR-0011](../docs/adr/0011-graph-data-model.md)).
- Fixed Cypher tools return `ToolResult` + `EvidencePath`; the agent composes answers from them ([ADR-0007](../docs/adr/0007-graph-query-strategy.md)).
- Deterministic structure first; the LLM is used only for Decision extraction and the agent ([ADR-0009](../docs/adr/0009-llm-via-openrouter.md)). Develop on Haiku 5.5 or GLM-5.3 Flash ([ADR-0010](../docs/adr/0010-llm-model-bake-off.md)).
- Writes go only to the sandbox, enforced in code and by the token's scope ([ADR-0005](../docs/adr/0005-triage-agent-writes-only-to-sandbox.md), [ADR-0012](../docs/adr/0012-deployment-and-sandbox.md)).

## Dependency graph

```
AEV-17 scaffold + FalkorDB check
 ├── AEV-18 ingest PRs ── AEV-19 ingest issues ── AEV-21 full ingest ──┬── AEV-24 extract ── AEV-25 decision_trail
 │        └────────────── AEV-20 experts_for ── AEV-22 3 tools ──┐     └── AEV-33 poller
 ├── AEV-23 LLM client (needs AEV-9 key) ────────────────────────┼──── AEV-24
 │                                                               └── AEV-26 agent + /api/ask ◄── AEV-25
 └── AEV-28 web ask view ──────────────── AEV-29 evidence graph ◄── AEV-26
AEV-26 ──► AEV-27 fallback · AEV-31 triage dry run · AEV-35 rate limit + cache · AEV-14 deploy (+AEV-28)
AEV-22 + AEV-25 ──► AEV-30 MCP
AEV-31 + AEV-13 sandbox repo ──► AEV-32 webhook + apply ──► AEV-36 README ──► AEV-8 make public
AEV-29 + AEV-31 ──► AEV-34 triage view
AEV-14 + AEV-29 + AEV-32 ──► AEV-37 demo video ──► AEV-38 submit ◄── AEV-8, AEV-36
AEV-24 + AEV-26 ──► AEV-11 bake-off          AEV-37 ──► AEV-39 blog
```

## Task list (ordered index)

Order is the recommended build sequence for one builder. **⇄** = safe to hand to a teammate in parallel. **✂** = cut if late.

### Phase 1: Foundation (slice 1: "who knows X" for one repo)

| # | Task | Size | Est. | Notes |
|---|---|---|---|---|
| 1 | **AEV-17** Scaffold repo, FalkorDB in Docker, verify Cypher functions | M | 1.5 h | Risk spike first |
| 2 | **AEV-18** Ingest PRs, reviews, files and components for one repo | M | 2 h | |
| 3 | **AEV-19** Ingest issues, comments, labels and references | M | 1.5 h | |
| 4 | **AEV-20** experts_for tool with evidence path and API endpoint | M | 1.5 h | |
| — | AEV-9 Set up OpenRouter key with a credit limit (manual) | XS | 0.25 h | ⇄ do any time before task 6 |
| — | AEV-13 Create aevion-sandbox repo and seed copied issues | S | 1 h | ⇄ |

**Checkpoint A: after AEV-20**
- [ ] Unit and integration tests pass; `/healthz` ok.
- [ ] "Who knows `<component>` in falkordb-py?" returns a sensible ranking with a valid evidence path through the API.
- [ ] Review with the team: is the Component granularity right (SPEC OQ-4)?

### Phase 2: Core (all five hero questions through `/api/ask`)

| # | Task | Size | Est. | Notes |
|---|---|---|---|---|
| 5 | **AEV-21** Full ingestion of 9 repos with CODEOWNERS and releases | M | 1.5 h | Start the full load, work on task 6 while it runs |
| 6 | **AEV-23** OpenRouter LLM client with cost tracking and cache | S | 1 h | ⇄ |
| 7 | **AEV-22** area_history, related_work and catch_up tools | M | 2 h | |
| 8 | **AEV-24** Decision extraction pipeline with cost dry-run | M | 2 h | Ask first if dry-run > $1 |
| 9 | **AEV-25** decision_trail tool with SUPERSEDES chain | S | 1 h | |
| 10 | **AEV-26** Agent loop and POST /api/ask | M | 2 h | |
| 11 | **AEV-28** Next.js ask view with generated API client | M | 2 h | ⇄ can start right after task 1 |

**Checkpoint B: after AEV-26**
- [ ] US-1 to US-5: 3 example questions each answered correctly through `/api/ask`, every evidence edge exists in the graph.
- [ ] LLM spend so far printed by `aevion cost`; on track for ≤ $12 total.

### Phase 3: Demo surface + Track 01

| # | Task | Size | Est. | Notes |
|---|---|---|---|---|
| 12 | **AEV-29** Evidence-path graph view and Show Cypher toggle | M | 2 h | Pick the graph library here (OQ-2) |
| 13 | **AEV-31** triage_candidates tool and dry-run triage API | M | 1.5 h | |
| 14 | **AEV-32** Sandbox webhook ingestion and triage apply | M | 1.5 h | Needs AEV-13 |
| 15 | **AEV-30** MCP server exposing the Cypher tools | S | 0.75 h | ⇄ |

**Checkpoint C/D: after AEV-32**
- [ ] Ask works end to end in the browser with the evidence graph.
- [ ] A replayed sandbox webhook produces label + assignee/mention + comment.
- [ ] Claude Code can call `experts_for` over MCP.

### Phase 4: Ship

| # | Task | Size | Est. | Notes |
|---|---|---|---|---|
| 16 | **AEV-14** Provision Railway (FalkorDB, API, poller) and Vercel | M | 1.5 h | Check Railway credit first (OQ-5) |
| 17 | **AEV-35** Rate limiting, CORS and cached hero answers | S | 1 h | Must be live before the URL is shared |
| 18 | **AEV-36** README setup, graph model and Cypher reference | S | 1 h | ⇄ |
| 19 | **AEV-37** Record and edit the demo video | M | 2 h | Follows the storyboard |
| 20 | **AEV-8** Make GitHub repo public for submission | XS | 0.1 h | Secret scan first |
| 21 | **AEV-38** Submit the project on WeMakeDevs | XS | 0.5 h | **Target 2026-10-18 20:00 IST** |

### Cut if late (in this order, first to go first)

| Task | If cut, instead… |
|---|---|
| AEV-39 Blog post for the side prize | Skip the side prize |
| AEV-11 Run LLM model bake-off | Keep Haiku 5.5 for extraction, Sonnet 5.5 or Haiku 5.5 for the agent |
| AEV-34 Triage view in the web app | Show triage happening in GitHub's own UI in the video |
| AEV-27 Guarded text-to-Cypher fallback | The agent says "I can't answer that yet" outside the six tools |
| AEV-33 Org poller | Re-run ingestion before recording; webhooks still show the "current" story |

## Time budget

| | Hours |
|---|---|
| Core tasks (phases 1–4) | ~28 |
| Cut-if-late tasks | ~6 |
| Available from now (17 Oct ~14:30 IST) to the 20:00 IST submit target on 18 Oct, minus ~6 h sleep | ~23–24 |

**Honest read:** the core scope is about 4–5 hours over budget for one person working at estimate speed. It fits only if AI-assisted tasks run faster than estimated, or if a teammate joins. Use the checkpoints to decide:

- **Behind at Checkpoint A** (later than ~19:00 IST today): merge AEV-22's three tools down to two (keep `catch_up`, drop `area_history`), and cut everything in the "cut if late" table.
- **Behind at Checkpoint B** (later than ~09:00 IST tomorrow): skip AEV-30 MCP and simplify AEV-29 to a static evidence list with links.
- **No matter what:** AEV-14 deploy starts by 14:00 IST tomorrow, and AEV-37 video by 17:00 IST.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| FalkorDB lacks a Cypher function we use (`exp`, date arithmetic) | High | AEV-17 tests it first; fall back to computing decay in Python on the query's rows |
| GitHub rate limits slow full ingestion | Med | GraphQL batching, conditional requests, cache raw responses on disk so a rerun skips the network |
| Decision extraction is noisy | Med | Strict candidate filter, confidence threshold, 10-item spot check; fewer, better Decisions beat many weak ones |
| Agent picks wrong tools or rambles | Med | Max 4 tool calls, tight system prompt, stubbed-LLM unit tests, eval questions from the bake-off set |
| LLM budget overrun | High | Cache + dry-run + credit limit on the key + rate limits + cached hero answers (ADR-0009) |
| Live demo breaks during judging | High | Cached hero answers; the video carries the story even if the URL is slow |
| Solo builder runs out of time | High | Checkpoint cut rules above; deploy and video have fixed start times |

## How each task is built (workflow)

Per task, in order:

1. **Start:** set the Notion task to In Progress; `git switch develop && git pull && git switch -c <type>/AEV-n`.
2. **Build:** Addy Osmani `incremental-implementation`, one thin slice at a time; Matt Pocock `tdd` at the agreed seams (each Cypher tool, ingestion normalisers, webhook HMAC, fallback guard).
3. **UI tasks:** Addy `frontend-ui-engineering`, then `browser-testing-with-devtools` to verify in a real browser.
4. **Review:** Addy `code-review-and-quality` on the diff before the PR.
5. **Ship the task:** commit `<type>: AEV-n - message` with a bullet body → PR into `develop` → squash-merge → **keep the branch** → Notion task Done with the PR link.
6. **Checkpoints:** run the checkpoint list above before moving to the next phase.

## Open questions carried from the spec

- OQ-1 duplicate detection (decided inside AEV-31: full-text + shared component/files first)
- OQ-2 graph library (decided inside AEV-29)
- OQ-3 work split (settled: one owner per task in Notion)
- OQ-4 component depth (reviewed at Checkpoint A)
- OQ-5 Railway credit (checked before AEV-14)
- OQ-6 cached answers in the graph (built in AEV-35)
