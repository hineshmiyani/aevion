# Spec: Aevion, a Company Brain on FalkorDB

**Status:** Draft v1, awaiting team approval · **Task:** AEV-6 · **Date:** 2026-10-17 · **Deadline:** 2026-10-18 23:59 IST

**Sources:** ADRs [0001](../adr/0001-company-brain-direction.md)–[0012](../adr/0012-deployment-and-sandbox.md), [GLOSSARY.md](../../GLOSSARY.md), [graph-model.md](../architecture/graph-model.md), [storyboard.md](../demo/storyboard.md). If this spec and an ADR disagree, the ADR wins until this spec is updated.

---

## 1. Objective

**Aevion** loads a public GitHub organisation into FalkorDB and answers questions about how that organisation works: who knows what, why things were decided, and what changed. Every answer carries the **evidence path** through the graph that produced it. A triage agent acts on what the graph shows.

- **User:** a maintainer or new contributor at an open-source company.
- **Demo org:** FalkorDB (9 repos, last 12 months).
- **Tracks:** 03 Company Brain (main), 01 Agents That Act on Connected Data.
- **Why a graph:** each hero question is a multi-hop traversal (person → PR → file → component → decision → comment). Without FalkorDB there is no product (Rule 3).

### User stories

| ID | As a… | I want to… | So that… |
|---|---|---|---|
| US-1 | contributor | ask "**Who knows** `<component>`?" | I ask the right person, with the PRs that prove it |
| US-2 | maintainer | ask "**Why was** `<thing>` **decided**?" | I see the decision, its rationale, alternatives, the discussion and who made it |
| US-3 | contributor | ask "**What's the history of** `<component>`?" | I see recent changes, open issues and active people in one place |
| US-4 | maintainer | ask "**What else does this touch?**" for an issue or PR | I see linked issues, shared files and affected components |
| US-5 | returning maintainer | ask "**Catch me up** on `<component or repo>` since `<date>`" | I get what changed and who drove it |
| US-6 | maintainer | have a new issue **triaged** automatically | duplicates, component, expert and a draft reply are ready, and on the sandbox they are applied |
| US-7 | developer using Claude Code or Cursor | call Aevion's tools **over MCP** | my coding agent can query the company brain |
| US-8 | anyone | trust that answers are **current** | new activity appears without a full reload, and superseded decisions are marked |

### Out of scope (v1)

Slack or Discord data · user accounts and login · claiming Track 02 · writing to any repo other than the sandbox · several orgs in the UI (the second org is config only) · mobile-specific UI · vector embeddings (unless round 3 decides otherwise).

---

## 2. Assumptions

These fill gaps no ADR covers. **Correct any of these in review.** Otherwise they stand.

1. Judges use the public URL without logging in, so the app has no authentication, only rate limits.
2. One GitHub token with read access to public data is enough to ingest 9 repos × 12 months within GitHub's rate limits (GraphQL preferred, REST where needed).
3. The FalkorDB Cypher features we rely on (`timestamp()`, `exp()`, full-text indexes, multigraph) behave as documented. **The first build slice verifies this.**
4. Demo traffic is small (under 50 concurrent users), so there is no horizontal scaling.
5. Content is English; desktop browsers first, readable on mobile.
6. Hero answers for the demo questions can be computed in advance and cached; the triage scene stays live.

---

## 3. Capability map

The product bundles several independently testable capabilities, so it is split into modules with fixed ids. Each module's requirements are in §9. Plans and tasks refer to these ids.

| Module id | Responsibility | Depends on |
|---|---|---|
| `graph-core` | FalkorDB connection, one graph per org, indexes, schema bootstrap | — |
| `llm` | OpenRouter client, `AGENT_MODEL` / `EXTRACTION_MODEL` config, cost tracking, response cache | — |
| `ingest` | Fetch GitHub data, normalise, filter bots, derive Components, MERGE into the org graph | `graph-core` |
| `extract` | Decision-candidate filter, LLM decision extraction, cost dry-run | `ingest`, `llm` |
| `tools` | Six fixed Cypher tools returning evidence paths, plus the guarded text-to-Cypher fallback | `graph-core` |
| `agent` | Agent loop: pick tools, call them, compose an answer that cites evidence | `tools`, `llm` |
| `sync` | Poller for the real org, GitHub webhook receiver for the sandbox | `ingest` |
| `triage` | Triage flow: dry run on real repos; apply on the sandbox only | `tools`, `agent`, `sync` |
| `mcp` | MCP server exposing the six tools | `tools` |
| `api` | FastAPI HTTP API, rate limiting, CORS, cached hero answers | `agent`, `triage`, `tools` |
| `web` | Next.js UI: ask, evidence-path view, triage view | `api` (contract in §8) |

**Build order:** `graph-core` + `llm` → `ingest` → `tools` → (`agent`, `mcp`, `extract` in parallel) → (`sync`, `triage`) → `api`.

`web` starts at the same time as `graph-core`, against a mocked API built from the contract in §8.

---

## 4. Tech stack

| Layer | Choice | Version policy |
|---|---|---|
| Language (backend) | Python | 3.13 |
| Package manager | uv | latest; `uv.lock` committed |
| Web framework | FastAPI + Uvicorn | pinned in `uv.lock` |
| Graph client | falkordb-py | pinned in `uv.lock` |
| MCP | official Python MCP SDK | pinned in `uv.lock` |
| HTTP client | httpx | pinned in `uv.lock` |
| Models / validation | Pydantic v2 | pinned in `uv.lock` |
| LLM access | OpenRouter (OpenAI-compatible API) | model IDs in config ([ADR-0010](../adr/0010-llm-model-bake-off.md)) |
| Frontend | Next.js + TypeScript (App Router) | current stable at scaffold time; pinned in lockfile |
| Node package manager | pnpm via Corepack | Node 22 |
| Database | `falkordb/falkordb` Docker image | **pin an exact tag** at scaffold time; never `latest` in deploy configs |
| Hosting | Railway (FalkorDB, API, poller) + Vercel (web) | [ADR-0012](../adr/0012-deployment-and-sandbox.md) |

---

## 5. Commands

These are the target commands; the scaffold task creates them. Run from the repo root unless noted.

```bash
# Infrastructure
docker compose -f infra/docker-compose.yml up -d falkordb

# Backend (apps/api)
uv sync --project apps/api
uv run --project apps/api uvicorn aevion.api.main:app --reload --port 8000
uv run --project apps/api pytest
uv run --project apps/api pytest -m integration        # needs FalkorDB running
uv run --project apps/api ruff check apps/api && uv run --project apps/api ruff format --check apps/api
uv run --project apps/api mypy apps/api/src

# Data
uv run --project apps/api aevion ingest --org-config config/orgs/falkordb.yaml
uv run --project apps/api aevion extract --org FalkorDB --dry-run   # prints projected LLM cost, writes nothing
uv run --project apps/api aevion extract --org FalkorDB
uv run --project apps/api aevion poll --org-config config/orgs/falkordb.yaml

# MCP (stdio)
uv run --project apps/api aevion mcp --org FalkorDB

# Frontend (apps/web)
corepack enable && pnpm --dir apps/web install
pnpm --dir apps/web dev
pnpm --dir apps/web lint && pnpm --dir apps/web typecheck && pnpm --dir apps/web build
```

---

## 6. Project structure

```
apps/
  api/
    pyproject.toml
    src/aevion/
      config.py              Settings from env (pydantic-settings)
      graph/                 graph-core: client, schema bootstrap, indexes
      llm/                   llm: OpenRouter client, cost tracking, cache
      ingest/                ingest: github fetchers, normalisers, components, loader
      extract/               extract: candidate filter, extractor, prompts
      tools/                 tools: one file per tool, evidence.py, fallback.py
      agent/                 agent: loop, system prompt
      sync/                  sync: poller, webhook verification + handling
      triage/                triage: service, sandbox writer (allow-listed)
      mcp/                   mcp: server
      api/                   api: FastAPI app, routes, rate limiting
      cli.py                 `aevion` CLI entry point
    tests/
      unit/                  Pure functions: normalisers, filters, scoring
      integration/           Real FalkorDB + fixture graph; one test file per tool
      fixtures/              Recorded GitHub JSON, fixture graph loader
  web/                       Next.js app (app/, components/, lib/api.ts generated types)
config/
  orgs/falkordb.yaml         Repos, since-date, component depth, label → component map
  orgs/sandbox.yaml
evals/                       Bake-off: labelled threads, known-answer questions, runner
infra/
  docker-compose.yml         Local FalkorDB
docs/                        As mapped in docs/README.md
```

---

## 7. Code style

**Python:** type hints everywhere, Pydantic models at module boundaries, `ruff` for lint and format, small functions. **Cypher is always parameterised.** User input never goes into a query string.

```python
class EvidencePath(BaseModel):
    nodes: list[EvidenceNode]
    edges: list[EvidenceEdge]


class ToolResult(BaseModel):
    tool: str
    rows: list[dict[str, Any]]
    evidence: EvidencePath
    cypher: str  # shown in the UI and the README


EXPERTS_FOR = """
MATCH (c:Component {key: $component})<-[:IN_COMPONENT]-(:File)<-[:MODIFIES]-(pr:PullRequest)
WHERE pr.merged_at IS NOT NULL
MATCH path = (p:Person)-[:AUTHORED|REVIEWED]->(pr)
WHERE NOT p.is_bot
...
"""


def experts_for(graph: OrgGraph, component: str, limit: int = 5) -> ToolResult:
    """Rank Experts for a Component by weighted, recent merged-PR activity."""
    result = graph.ro_query(EXPERTS_FOR, {"component": component, "limit": limit})
    return ToolResult(
        tool="experts_for",
        rows=result.rows,
        evidence=evidence_from_paths(result.paths),
        cypher=EXPERTS_FOR,
    )
```

**TypeScript:** strict mode; API types generated from FastAPI's OpenAPI schema (`lib/api.ts`), never hand-written; server components by default; no `any`.

**Naming:** use [GLOSSARY.md](../../GLOSSARY.md) terms exactly: `Component`, `Expert`, `Owner`, `Decision`, `EvidencePath`, `Tool`, `Triage`, `Sandbox`.

---

## 8. API contract (draft)

| Method + path | Request | Response | Module |
|---|---|---|---|
| `POST /api/ask` | `{org, question}` | `{answer, tool_calls: [{tool, args}], evidence: EvidencePath, cypher: [string], model, cached}` | `api` → `agent` |
| `POST /api/tools/{tool}` | tool parameters | `ToolResult` | `api` → `tools` |
| `POST /api/triage` | `{org, issue_key, mode: "dry_run" \| "apply"}` | `{duplicates, component, expert, draft_reply, actions: [{type, status}], evidence}` | `api` → `triage` |
| `GET /api/graph/neighborhood` | `?org&key&depth≤2` | `EvidencePath` | `api` → `graph-core` |
| `POST /webhooks/github` | GitHub webhook payload (HMAC-verified) | `202` | `sync` |
| `GET /healthz` | — | `{falkordb: "ok", graphs: [...]}` | `api` |

`EvidencePath` = `{nodes: [{id, label, title, url?}], edges: [{source, target, type}]}`. Every edge in it must exist in the graph.

---

## 9. Module requirements

### `graph-core`
- Connect using `FALKORDB_URL`; one graph per org named `org:<OrgName>`.
- Idempotent bootstrap creates every index in [graph-model.md](../architecture/graph-model.md).
- A read-only query helper (`ro_query`, using `GRAPH.RO_QUERY`) that every tool and the fallback must use.

### `llm`
- One client for OpenRouter's OpenAI-compatible API, with tool calling; models come from `AGENT_MODEL` / `EXTRACTION_MODEL`.
- Every call records tokens and cost (reasoning tokens included); `aevion cost` prints totals.
- Responses are cached by content hash; a re-run costs $0.

### `ingest`
- Inputs come from `config/orgs/*.yaml`: repos, since-date, component depth (default 2), and the label → component map.
- Loads issues, PRs, reviews, review comments, issue comments, PR file lists, CODEOWNERS (current + history), labels, releases and docs markdown paths.
- Bots are excluded: `[bot]` suffix, `type == "Bot"`, plus a configurable deny-list.
- References come from closing keywords, GitHub's closing references, and `#n` / `owner/repo#n` mentions.
- Every write is a MERGE on the stable key, so re-running ingestion creates no duplicates.

### `extract`
- Candidate filter as specified in graph-model.md; `--dry-run` prints candidate count, token estimate and projected cost.
- Output is validated against a schema; low-confidence results (< 0.5) are dropped; the model ID is recorded on each `Decision`.

### `tools`
- `experts_for`, `decision_trail`, `area_history`, `related_work`, `catch_up` and `triage_candidates`, each returning a `ToolResult` with an evidence path.
- Fallback: text-to-Cypher, **read-only** (runs via `ro_query`; write clauses rejected before execution), forced `LIMIT 50`, a 3-second timeout, and the generated Cypher shown to the user.

### `agent`
- Uses tools before the fallback; at most 4 tool calls per question; the answer cites evidence nodes; it says "I don't know" when the tools return nothing.

### `sync`
- Poller: every 5 minutes per repo, fetching only what changed since the last run, using conditional requests.
- Webhook: verifies the HMAC signature and ingests sandbox issue and comment events into `org:aevion-sandbox` within 10 seconds.

### `triage`
- `dry_run` works on any repo; `apply` is rejected unless the repo is on the allow-list (`hineshmiyani/aevion-sandbox`) **and** the sandbox token is used.
- Apply actions: add a component label, assign the Expert (if they're a collaborator, otherwise mention them), post the draft reply with its evidence links.

### `mcp`
- Exposes the six tools with JSON schemas; the org is chosen with `--org`.

### `api`
- CORS restricted to the Vercel domain; rate limit of 10 asks per minute per IP and 100 per day per IP; hero answers served from cache.

### `web`
- **Ask view:** question box with the five hero questions as suggestion chips; answer with inline citations; an interactive evidence-path graph; a "Show Cypher" toggle.
- **Triage view:** pick an issue, run a dry run or apply (sandbox only), see each action's status.
- Graph library to be decided in round 3.

---

## 10. Testing strategy

| Level | What | Where | Tooling |
|---|---|---|---|
| Unit | Normalisers, bot filter, component derivation, candidate filter, Cypher write-clause rejection, webhook HMAC | `apps/api/tests/unit` | pytest |
| Integration | **Each tool at its seam** against real FalkorDB loaded with a small fixture graph; ingestion idempotence (load twice, compare counts); evidence edges exist in the graph | `apps/api/tests/integration` (`-m integration`) | pytest + FalkorDB in Docker |
| Eval | Bake-off set: 20 labelled threads, 10 known-answer questions; becomes the regression suite | `evals/` | custom runner |
| Frontend | Typecheck, lint, build; one Playwright smoke test of the ask flow against the mocked API | `apps/web` | tsc, eslint, Playwright |

No coverage percentage target. Every module seam in §9 has at least one test, and every tool has an integration test.

---

## 11. Non-functional requirements

| Concern | Target |
|---|---|
| Tool query latency | p95 < 300 ms on the demo graph |
| Ask latency | p50 < 8 s live; < 200 ms for cached hero answers |
| Webhook → graph | < 10 s |
| Full ingestion (demo dataset) | < 30 min |
| LLM spend | ≤ $12 total by submission (out of $16), as reported by `aevion cost` and OpenRouter |
| Security | Secrets only in `.env` and platform stores; FalkorDB not publicly exposed; parameterised Cypher; read-only fallback; sandbox allow-list plus a token limited to the sandbox |

---

## 12. Boundaries

**Always**
- Branch from `develop` as `<type>/AEV-n`; commit `<type>: AEV-n - message` with a bullet body; PR into `develop`.
- Parameterise Cypher; return an evidence path from every tool.
- Update `graph-model.md` / `cypher-queries.md` in the same PR as schema or query changes.
- Run unit tests (and integration tests for `tools` / `ingest` changes) before opening a PR.

**Ask first** (raise in the PR or team chat)
- Changing the graph schema beyond graph-model.md.
- Adding a dependency, a second datastore, or a vector index.
- Any single LLM run projected over $1.
- Changing the deployment platform or its secrets.

**Never**
- Write to any GitHub repo other than `hineshmiyani/aevion-sandbox`.
- Load login-protected, private or personal data.
- Commit secrets, tokens or `.env` files.
- Add AI attribution to code, commits or PRs.
- Ship a feature that works without FalkorDB.

---

## 13. Success criteria

The spec is done when all of these are true and verified:

1. **Ingestion:** `org:FalkorDB` holds the 9 repos × 12 months; a second run adds 0 nodes and 0 edges.
2. **Hero questions:** for each of US-1–US-5, 3 example questions return correct answers (checked by hand against GitHub) with an evidence path whose every edge exists in the graph (automated test).
3. **Decisions:** at least 30 Decisions extracted from FalkorDB repos; 10 spot-checked by a teammate as accurate.
4. **Triage:** a dry run on a real FalkorDB issue returns a component, at least 1 related issue, an Expert and a draft reply. Filing an issue on the sandbox produces a label, an assignee or mention, and a comment **within 30 seconds**, through the webhook.
5. **Freshness:** a new sandbox event is in the graph within 10 seconds; the poller picks up new org activity within 10 minutes; a superseded Decision shows its `SUPERSEDES` link.
6. **MCP:** Claude Code lists the six tools and gets a correct answer from `experts_for`.
7. **Fallback safety:** a test proves write Cypher (`CREATE`, `MERGE`, `SET`, `DELETE`, `REMOVE`, `DROP`) is rejected.
8. **Deployed:** the Vercel URL and the Railway API are live; `/healthz` reports FalkorDB ok.
9. **Budget:** total LLM spend ≤ $12.
10. **Submission:** README has setup, the graph model and the Cypher reference; the demo video follows the storyboard; the repo is public; tracks 03 + 01 are named.

---

## 14. Open questions

| # | Question | Blocks | Proposed handling |
|---|---|---|---|
| OQ-1 | Duplicate detection: full-text index only, or vector embeddings? | `tools.triage_candidates` | Start with full-text plus shared Component and shared File signals; revisit if dry-run quality is poor |
| OQ-2 | Graph visualisation library for the evidence path | `web` | Round 3 |
| OQ-3 | Final work split | all | Confirm with Jignesh and Jaydeep (Notion task) |
| OQ-4 | Component depth per repo (default 2) | `ingest` | Check after the first ingestion; tune in `config/orgs/falkordb.yaml` |
| OQ-5 | Railway credit available? | deployment | Check before the provisioning task |
| OQ-6 | Where cached hero answers live | `api` | Proposed: in the org graph as `(:CachedAnswer)` nodes, so FalkorDB stays the only datastore |
