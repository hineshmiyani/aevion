# Grilling round 1: core product decisions

**Status:** 🟡 Awaiting answers · **Opened:** 2026-10-17 · **Deciders:** the team (Hinesh, Jignesh, Jaydeep, Het)

This round covers the decisions that don't depend on each other. Each question has a recommended answer. **Reply "yes" to accept it, or write your change in the Answer line.** Teammates: add a comment line under any question you disagree with, starting with your name.

Once every question is answered, the significant ones become ADRs in [`docs/adr/`](../adr/) and round 2 opens.

## Facts gathered before this round

- The project folder was empty; Docker, Node 22, Python 3.13 and `gh` are installed (`pnpm` and `uv` are not).
- FalkorDB org: ~4,300 issues and ~10,600 PRs total; ~2,400 PRs merged in the last 6 months.
- FalkorDB already ships `FalkorDB-MCPServer`, `text-to-cypher`, `code-graph` and `QueryWeaver`.

---

## Q1: Tracks to claim

Submit to **Track 03 (Company Brain)** as the main track and **Track 01 (Agents That Act)** as the second. Do **not** claim Track 02, even though some memory features will exist: a weak claim there could make judges doubt the other two.

➡️ **Recommended:** 03 + 01, skip 02.

**Answer:** _pending_

---

## Q2: Data sources

Pull everything from public GitHub: issues, PRs, review comments, commits, CODEOWNERS, docs markdown, releases. Skip Discord and Slack: FalkorDB's Discord requires a login, so Rule 6 arguably forbids it, and a second ingestion pipeline would cost about a third of our time. "Docs, tickets and chats" map to markdown docs, issues, and PR/issue comment threads.

➡️ **Recommended:** GitHub only.

**Answer:** _pending_

---

## Q3: Repos and how far back

Pin about 9 core repos (FalkorDB, GraphRAG-SDK, QueryWeaver, code-graph, falkordb-browser, falkordb-py, falkordb-ts, FalkorDB-MCPServer, docs) for the last **12 months**, with bot accounts filtered out. The ingester stays generic, so any public org works; this is just the demo dataset.

➡️ **Recommended:** those 9 repos, 12 months, bots filtered out, generic ingester.

**Answer:** _pending_

---

## Q4: Persona and the five questions

The persona is a **maintainer or new contributor** at an open-source company. The five questions the product must answer brilliantly:

1. **Who knows X?** Experts ranked by commits, reviews and fixes.
2. **Why was X decided?** The trail from decision to PR to review discussion to original issue.
3. **What's the history of X?** Recent changes, open issues and active people in one area.
4. **What else does this touch?** Linked issues, shared files, affected components.
5. **Catch me up:** what changed in area X since a given date, and who drove it.

➡️ **Recommended:** lock these five; nothing else until all five are polished.

**Answer:** _pending_

---

## Q5: What the Track 01 agent does

When a new issue arrives, the triage agent finds duplicates and related issues, works out which component it touches, picks the best owner from the expertise graph, drafts a reply, then **applies labels, assigns the owner and posts the comment**. Write actions happen **only on a sandbox repo we own**. On FalkorDB's real repos it is read-only and shows "here's what I would do".

➡️ **Recommended:** real actions on our sandbox, dry-run on the real org.

**Answer:** _pending_

---

## Q6: Keeping the graph current

We can't install webhooks on an org we don't own, so:

- **Real org:** poll GitHub every few minutes, using requests that only return data when something changed.
- **Sandbox repo:** real webhooks, so the live demo shows an issue filed, the graph updated within seconds, and the agent triaging it.

Superseded facts are kept with time ranges rather than overwritten.

➡️ **Recommended:** polling for the org, webhooks for the sandbox, history kept.

**Answer:** _pending_

---

## Q7: How the agent queries the graph

Mainly **a curated set of fixed, parameterised Cypher tools**, roughly one per hero question (`experts_for`, `decision_trail`, `area_history`, `related_work`, `catch_up`, `triage_candidates`). Behind them, **a read-only, size-limited fallback that generates Cypher from plain English** for anything else. Fixed tools are fast, correct, and listable in the README (Rule 10).

➡️ **Recommended:** curated tools first, guarded text-to-Cypher fallback.

**Answer:** _pending_

---

## Q8: Tech stack

A **Python FastAPI backend** for ingestion, the agent, the MCP server and the FalkorDB client (falkordb-py and the Python MCP SDK are the most mature). A **Next.js + TypeScript frontend** for the chat UI and graph visualisation. `uv` for Python dependencies.

**Needs input from all three teammates:** which language is each of you fastest in?

➡️ **Recommended:** FastAPI (Python) + Next.js (TS).

**Answer:** _pending_

---

## Q9: LLM and API key

Claude **Sonnet 5.5** for the agent's reasoning and tool use; **Haiku 5.5** for bulk extraction, such as pulling decisions and topics out of thousands of PR threads cheaply. No API key is set in the environment yet.

➡️ **Recommended:** Sonnet 5.5 + Haiku 5.5, assuming we have a key with enough budget for one ingestion of about 10k threads plus demo traffic.

**Answer:** _pending_

---

## Coming in round 2 (blocked on this round)

- Graph schema: node labels, relationships, temporal properties (depends on Q2, Q3, Q4)
- Deployment: FalkorDB Cloud vs. self-hosted; where the backend and frontend run (depends on Q8)
- Work split across the three teammates (depends on Q8)
- Product name
- Demo video storyboard (depends on Q4, Q5)
