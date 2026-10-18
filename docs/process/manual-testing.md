# Manual testing guide

How to check Aevion by hand, in production and locally. Use it before recording the demo and before submitting.

## Test questions

### Instant: cached hero answers

These are the starter questions on the Ask page. They answer in well under a second and come from the graph's cache (`cached: true`), so they never count toward the rate limit.

1. Who knows the falkordb-py client code best?
2. Why did FalkorDB gate main on a merge queue?
3. What's been happening in GraphRAG-SDK's ingestion code lately?
4. What else does FalkorDB/FalkorDB#3176 touch?
5. Catch me up on falkordb-browser since October 1.

### Live: answered by the agent (4 to 8 seconds each)

Type these into the ask box.

| Tool | Question | A good answer… |
|---|---|---|
| Experts | Who reviews most of the GraphRAG-SDK pull requests? | puts galshubeli first, then Naseem77 |
| Experts | Who should I ask about FalkorDB's query execution plan? | names swilly22, DvirDukhan and others, with their PRs |
| Decisions | Why are GitHub Actions pinned to commit SHAs? | explains supply-chain safety and cites the PR |
| Decisions | Why does GraphRAG-SDK derive chunk ids deterministically? | says re-ingesting created duplicate chunks (17 → 34 → 51) |
| Decisions | Why does the browser's Load CSV use FalkorDB's native LOAD CSV? | mentions handling large files without exhausting memory |
| History | What's been happening in FalkorDB's UDF code lately? | lists recent PRs and issues in `src/udf` |
| Related | What else does FalkorDB/GraphRAG-SDK#309 touch? | shows files, Components and overlapping PRs |
| Catch-up | What changed in falkordb-py in the last month? | lists merged PRs and releases |
| Honesty | Who maintains FalkorDB's Kubernetes operator? | says it doesn't know, rather than inventing someone |

### Triage page (`/triage`)

- **Dry runs:** use the starters `FalkorDB/FalkorDB#3357` (area `src/udf`, Expert swilly22), `FalkorDB/falkordb-py#306` and `FalkorDB/GraphRAG-SDK#344`.
- **A hedged answer:** type `FalkorDB/FalkorDB#3371`. Its area should be marked **weak**, and the reply should say the area is a guess.
- **A sandbox issue (production only):** the starter `hineshmiyani/aevion-sandbox#37` shows what Aevion already did there: a label and a posted comment.

### Check on every answer

- [ ] Clicking a citation number highlights the same row in the "Where this comes from" trail.
- [ ] Clicking a node in "The graph behind this answer" highlights it and shows "Open on GitHub".
- [ ] "Show Cypher" lists the queries that ran.
- [ ] The page works at phone width, and in dark mode.
- [ ] No answer @-mentions anyone (people are named by profile link).

## Testing in production

1. Open **https://aevion-alpha.vercel.app** and try the questions above.
2. Open **https://aevion-alpha.vercel.app/triage** and run the triage tests.
3. Test the triage agent end to end: [open a new issue on the sandbox](https://github.com/hineshmiyani/aevion-sandbox/issues/new), for example *"TypeScript client loses the connection after a Redis failover"*. Within about 10 seconds it should get an `area: …` label and a comment that:
   - names an Expert by profile link, with no @;
   - writes FalkorDB issues as code (like `FalkorDB/FalkorDB#123`), not as links.
4. Check the backend: https://api-production-ae7a.up.railway.app/healthz should list both graphs.

Live questions are limited to **10 a minute and 100 a day per visitor**. Cached starter questions don't count.

## Testing locally

Pick the option that matches what you want to test.

### Option A: the web app against the production API (quickest)

No database, keys or graph build needed. The local Next.js server calls production's API server-side.

```bash
corepack enable && pnpm --dir apps/web install
```

```bash
AEVION_API_URL=https://api-production-ae7a.up.railway.app pnpm --dir apps/web dev --port 3001
```

Open http://localhost:3001 and http://localhost:3001/triage. Live questions count toward your rate limit, the same as in production.

### Option B: web app only, with recorded answers

With `AEVION_API_URL` unset, the app serves a built-in sample answer and a sample triage. This is useful for UI work and is what the Playwright tests use.

```bash
pnpm --dir apps/web dev --port 3001
```

### Option C: everything on your machine

You need Docker, [uv](https://docs.astral.sh/uv/) 0.13+, Node 22 with Corepack, a GitHub token (or `gh auth login`) and an OpenRouter key in `.env`. See the [README](../../README.md#run-it-locally).

1. Start FalkorDB:
   ```bash
   docker compose -f infra/docker-compose.yml up -d
   ```
2. Build the graph (about 10 minutes), extract Decisions (about $0.40 of LLM calls) and cache the hero answers:
   ```bash
   uv run --project apps/api aevion ingest
   ```
   ```bash
   uv run --project apps/api aevion extract
   ```
   ```bash
   uv run --project apps/api aevion warm-cache
   ```
3. Start the API:
   ```bash
   uv run --project apps/api uvicorn aevion.api.main:app --port 8000
   ```
4. Start the web app, then open http://localhost:3001 (FalkorDB's Docker image serves its own browser UI on port 3000, so the web app uses 3001.):
   ```bash
   AEVION_API_URL=http://localhost:8000 pnpm --dir apps/web dev --port 3001
   ```
5. Check http://localhost:8000/healthz lists `org:falkordb`.

Next.js allows only one `dev` server per app folder. If it says another one is running, stop that one first.

### Local limits

- **New sandbox issues aren't triaged locally.** GitHub's webhook points at production, so the "open a new issue" test only works there.
- **Don't use "Act on the issue" locally** if your `.env` has `SANDBOX_GITHUB_TOKEN`. A local run doesn't know what production already did, so it would post a real second comment on the sandbox. Dry runs are always safe.

## Automated tests

```bash
uv run --project apps/api pytest
```

```bash
pnpm --dir apps/web test:e2e
```

The API suite needs the local FalkorDB from Docker for its integration tests. The model and GitHub are always mocked, and the sandbox writer refuses to reach the real GitHub during tests. The Playwright tests run the web app against its recorded samples on desktop and mobile; run `pnpm --dir apps/web exec playwright install chromium` once first.

## Reporting a problem

Post in the team chat with:

- the page URL and whether it was production or local;
- the question or issue key;
- a screenshot of the answer;
- the "Show Cypher" queries, if the answer looks wrong.

The Cypher shows exactly which part of the graph the answer came from, which is usually enough to trace the cause.
