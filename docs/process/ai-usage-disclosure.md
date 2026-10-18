# AI usage disclosure

Graph Hacks Rule 11 allows AI coding assistants but requires disclosure. This page is our disclosure. It is linked
from the README and the submission.

## What we did ourselves

- **Chose the product and the tracks:** a company brain for FalkorDB's GitHub org (Track 03) with an agent that acts
  on it (Track 01), after comparing the track ideas.
- **Designed the graph model** in two rounds of questions: the node types, the relationships, which data to load
  (9 main repos, the last 12 months, bots filtered out) and how it stays fresh.
- **Set the safety rules:** the agent writes only to our own sandbox repo, never to FalkorDB's repos, and it never
  @-mentions real people (ADR-0005, ADR-0013).
- **Picked the stack and the budget:** FastAPI and Next.js, models through OpenRouter with spending caps.
- **Checked the answers against real data:** expert rankings, decision trails and triage picks were compared with
  real FalkorDB pull requests and issues before we accepted them.
- **Directed the design:** the survey-map look, square corners and the light theme, and which review items to build.
- **Ran the project:** split the work into Notion tasks with owners, and reviewed and merged every branch.

## Log

One row per area of the product. Together they cover every session where an AI assistant helped build Aevion.
**Who** is the teammate who owned that area's tasks in Notion.

| Dates | Area | Who | What the AI helped with | What we decided or checked |
|---|---|---|---|---|
| Oct 17–18 | Planning and docs | Team | Ran our design questions as multiple-choice rounds; drafted the ADRs (0001–0013), the spec, the glossary, the demo storyboard, the implementation plan, the README and the testing guide; compared OpenRouter model prices | Answered every design question; chose the direction, tracks, data scope, stack and models; approved the spec and the task split; reviewed the README against the hackathon's requirements |
| Oct 17 | Ingestion and graph model | Hinesh | Scaffolded the API and the local FalkorDB setup with feature tests; built ingestion for pull requests, reviews, issues, comments, labels, references, CODEOWNERS and releases | Chose how teams and code areas are modelled; tuned code-area depth per repo; checked the graph's shape on real falkordb-py data |
| Oct 17–18 | Query tools, LLM and agent | Jaydeep, Hinesh, Het | Built the query tools (experts, area history, related work, catch-up, decision trail), decision extraction and its retry fix, the OpenRouter client with cache and budget guard, the agent loop with numbered sources, the ask API with rate limits and cached answers, and the MCP server | Checked expert rankings and answers on real data; spot-checked 26 extracted decisions; chose thread links over model judgement for superseded decisions; kept a confidence floor and spending caps |
| Oct 17–18 | Triage agent | Hinesh, Jaydeep | Built triage (similar issues, which repo and code area an issue is about, who knows it), the dry-run API, the sandbox writer and seeded issues, the signed GitHub webhook and the act-on-issue flow; added a guard so tests can never post to GitHub; fixed a triage query that timed out in production | Created the sandbox repo and its scoped token; decided triage never @-mentions people and only writes to the sandbox; tuned the picks on real issues |
| Oct 17–18 | Web app | Jignesh, Het | Built the ask view, the evidence graph and Cypher views, and the triage view; rebuilt the UI as a survey map after a design review; added live progress and graph statistics to the API; implemented the review fixes (empty and loading states, shareable answer links, readable Cypher, a keyboard shortcut, phone layout, map layout, type sizes, thin scrollbars); added Playwright and accessibility tests | Chose the visual direction (survey map, square corners, light theme); picked which review items to build; reviewed every screen in the browser on desktop and mobile |
