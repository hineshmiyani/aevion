# Grilling round 2: graph model, deployment, team, name, demo

**Status:** ✅ Answered 2026-10-17 (Q9 provisional until teammates confirm) · **Deciders:** the team (Hinesh, Jignesh, Jaydeep, Het) · **Builds on:** [round 1](round-01.md), ADRs 0004–0010

Asked interactively as multiple-choice questions, with the recommended option first. Outcomes are recorded in [ADR-0011](../adr/0011-graph-data-model.md) (graph model), [ADR-0012](../adr/0012-deployment-and-sandbox.md) (deployment and sandbox), [docs/architecture/graph-model.md](../architecture/graph-model.md) and [docs/demo/storyboard.md](../demo/storyboard.md).

**Facts gathered before this round:** FalkorDB Cloud's free tier supports multiple graphs, but has no TLS, no continuous persistence and no automated backups (falkordb.com/plans, 2026-10-17).

## Graph model

| # | Question | Options offered | Answer |
|---|---|---|---|
| Q1 | What is a Component (the X in "who knows X")? | **Paths + labels** · LLM topics · Repo = component | **Paths + labels.** Directory prefixes plus GitHub labels mapped onto them. No LLM cost. |
| Q2 | How are PR/issue comments stored? | **Comment nodes** · Edges only · Hybrid | **Comment nodes**, so evidence can cite the exact comment. |
| Q3 | How is expertise computed? | **Live Cypher query** · Precomputed EXPERT_IN edges · Live query + PageRank | **Live weighted Cypher query** with recency decay, run at question time. |
| Q4 | What becomes a Decision node? | **Filtered LLM extraction** · Every merged PR · Labelled/RFC only | **Filtered LLM extraction.** A cheap filter picks candidate threads; the extraction model writes the Decision. |
| Q5 | How is each org's data isolated? | **One graph per org** · Single graph | **One FalkorDB graph per org** (multigraph). |
| Q6 | Which facts carry validity time ranges? | **Minimal set** · Everything versioned · Nothing versioned | **Minimal set:** `OWNS` edges and the Decision `SUPERSEDES` chain. |

## Deployment

| # | Question | Options offered | Answer |
|---|---|---|---|
| Q7 | Where does FalkorDB run? | **Self-host on Railway** · FalkorDB Cloud free tier · Self-host on Fly.io | **Self-hosted Docker on Railway** with a persistent volume. |
| Q8 | Where do the backend, poller and frontend run? | **Railway + Vercel** · All on Railway · Render + Vercel | **Railway** (API, poller, FalkorDB) + **Vercel** (Next.js). |
| Q12 | What is the triage sandbox repo? | **hineshmiyani/aevion-sandbox** · Separate GitHub org · Use the main repo | **`hineshmiyani/aevion-sandbox`**, seeded with ~30 copied FalkorDB issues. |

## Team, name, demo

| # | Question | Options offered | Answer |
|---|---|---|---|
| Q9 | How do we split the work? | By layer · Hinesh on ingestion · **Decide with teammates** | **Provisional, to be confirmed with Jignesh and Jaydeep** (see below). |
| Q10 | Product name? | **Aevion** · Provenance · Tribal | **Aevion**, the same as the team name. |
| Q11 | Shape of the demo video? | **Judge's-org hook** · Problem-first · Architecture-first | **Judge's-org hook.** See [storyboard](../demo/storyboard.md). |

### Provisional work split (Q9)

Confirm or swap owners with Jignesh and Jaydeep (Notion task "Confirm work split with teammates"). Until then:

| Area | Provisional owner |
|---|---|
| GitHub ingestion, graph model, agent loop, decision trail, triage tool, deployment | Hinesh |
| Next.js ask view, shareable answers, readable Cypher, review polish | Jignesh |
| Cypher tools, LLM client, decision extraction, sandbox webhook, rate limits | Jaydeep |
| Evidence-path graph, MCP server, triage view, survey-map UI rebuild | Het |

## Open questions for round 3

- **Duplicate detection for triage:** FalkorDB full-text index only, or add vector embeddings (needs an embeddings model and budget)?
- **Evidence-path visualisation:** which graph library in Next.js?
- **API contract:** endpoint shapes between FastAPI and Next.js.
