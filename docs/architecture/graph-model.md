# Graph data model

**Status:** v1 design, 2026-10-17 ([ADR-0011](../adr/0011-graph-data-model.md)). Keep this file in sync with the ingestion code; the README's graph-model section is generated from it.

## Graphs

FalkorDB holds **one graph per org** (multigraph):

| Graph | Contents |
|---|---|
| `org:FalkorDB` | The 9 demo repos, last 12 months ([ADR-0004](../adr/0004-product-scope-and-data.md)) |
| `org:aevion-sandbox` | `hineshmiyani/aevion-sandbox`, for the live triage demo |

## Diagram

```mermaid
graph LR
  Person -- AUTHORED --> Issue
  Person -- AUTHORED --> PullRequest
  Person -- AUTHORED --> Comment
  Person -- REVIEWED --> PullRequest
  Person -- OWNS --> Component
  Comment -- ON --> Issue
  Comment -- ON --> PullRequest
  PullRequest -- FIXES --> Issue
  PullRequest -- REFERENCES --> Issue
  Issue -- REFERENCES --> Issue
  PullRequest -- MODIFIES --> File
  File -- IN_COMPONENT --> Component
  Label -- MAPS_TO --> Component
  Issue -- HAS_LABEL --> Label
  PullRequest -- HAS_LABEL --> Label
  Issue -- ASSIGNED_TO --> Person
  Component -- IN_REPO --> Repo
  Issue -- IN_REPO --> Repo
  PullRequest -- IN_REPO --> Repo
  Release -- INCLUDES --> PullRequest
  Decision -- DECIDED_IN --> PullRequest
  Decision -- DECIDED_IN --> Issue
  Decision -- EVIDENCED_BY --> Comment
  Decision -- MADE_BY --> Person
  Decision -- AFFECTS --> Component
  Decision -- SUPERSEDES --> Decision
```

## Node labels

All times are **epoch milliseconds** (integers). `key` is the MERGE key and is unique within a graph.

| Label | Key | Properties | Source |
|---|---|---|---|
| `Repo` | `full_name` (`FalkorDB/FalkorDB`) | `name`, `url`, `stars`, `default_branch` | GitHub API |
| `Person` | `login` | `name`, `avatar_url`, `is_bot` | GitHub API |
| `Issue` | `key` (`FalkorDB/FalkorDB#123`) | `number`, `title`, `body_excerpt`, `state`, `created_at`, `closed_at`, `url` | GitHub API |
| `PullRequest` | `key` (`FalkorDB/FalkorDB#456`) | `number`, `title`, `body_excerpt`, `state`, `created_at`, `merged_at`, `url`, `additions`, `deletions` | GitHub API |
| `Comment` | `id` (GitHub ID) | `kind` (`issue` / `review` / `review_thread`), `excerpt`, `created_at`, `url` | GitHub API |
| `File` | `key` (`FalkorDB/FalkorDB:src/x.c`) | `path`, `repo`, `is_doc` | PR file lists |
| `Component` | `key` (`FalkorDB/FalkorDB:src/execution_plan`) | `name`, `repo`, `path_prefix`, `source` (`path` / `label`) | Derived: directory prefix (default depth 2) |
| `Label` | `key` (`FalkorDB/FalkorDB:bug`) | `name`, `color` | GitHub API |
| `Release` | `key` (`FalkorDB/FalkorDB@v4.8.0`) | `tag`, `published_at`, `url` | GitHub API |
| `Decision` | `id` (content hash) | `summary`, `rationale`, `alternatives`, `decided_at`, `confidence`, `model`, `source_url` | LLM extraction ([ADR-0010](../adr/0010-llm-model-bake-off.md)) |

## Relationship types

| Type | From → To | Properties | Notes |
|---|---|---|---|
| `AUTHORED` | Person → Issue / PullRequest / Comment | `at` | |
| `REVIEWED` | Person → PullRequest | `state` (`APPROVED` / `CHANGES_REQUESTED` / `COMMENTED`), `at` | |
| `ON` | Comment → Issue / PullRequest | | |
| `FIXES` | PullRequest → Issue | | From closing keywords and GitHub's closing references |
| `REFERENCES` | Issue / PullRequest → Issue / PullRequest | `at` | From `#123` / `owner/repo#123` mentions |
| `MODIFIES` | PullRequest → File | `additions`, `deletions` | |
| `IN_COMPONENT` | File → Component | | |
| `MAPS_TO` | Label → Component | | Per-repo config |
| `HAS_LABEL` | Issue / PullRequest → Label | | |
| `ASSIGNED_TO` | Issue → Person | | |
| `IN_REPO` | Component / Issue / PullRequest → Repo | | |
| `OWNS` | Person → Component | `source` (`CODEOWNERS`), **`valid_from`, `valid_to`** | Time-ranged; `valid_to = null` means current |
| `INCLUDES` | Release → PullRequest | | From release notes |
| `DECIDED_IN` | Decision → PullRequest / Issue | | |
| `EVIDENCED_BY` | Decision → Comment | | The comments the extraction cited |
| `MADE_BY` | Decision → Person | | |
| `AFFECTS` | Decision → Component | | |
| `SUPERSEDES` | Decision → Decision | `at` | Time chain for "what did we believe before?" |

## Indexes

```cypher
CREATE INDEX FOR (p:Person) ON (p.login)
CREATE INDEX FOR (i:Issue) ON (i.key)
CREATE INDEX FOR (pr:PullRequest) ON (pr.key)
CREATE INDEX FOR (c:Comment) ON (c.id)
CREATE INDEX FOR (f:File) ON (f.key)
CREATE INDEX FOR (c:Component) ON (c.key)
CREATE INDEX FOR (d:Decision) ON (d.id)
CREATE INDEX FOR (pr:PullRequest) ON (pr.merged_at)
CALL db.idx.fulltext.createNodeIndex('Issue', 'title', 'body_excerpt')
CALL db.idx.fulltext.createNodeIndex('Decision', 'summary', 'rationale')
```

## Expertise query (sketch)

"Who knows component X?" is answered live ([ADR-0011](../adr/0011-graph-data-model.md) §3). The weights are design constants: merged PR authored 3, review 2, comment 0.5, with exponential recency decay (half-life ~180 days). The **evidence** is the list of PRs behind each score.

```cypher
// Sketch only: verify function support against FalkorDB during implementation.
MATCH (c:Component {key: $component})<-[:IN_COMPONENT]-(:File)<-[:MODIFIES]-(pr:PullRequest)
WHERE pr.merged_at IS NOT NULL
MATCH (p:Person)-[r:AUTHORED|REVIEWED]->(pr)
WHERE NOT p.is_bot
WITH p, pr,
     CASE type(r) WHEN 'AUTHORED' THEN 3.0 ELSE 2.0 END AS weight,
     (timestamp() - pr.merged_at) / 86400000.0 AS age_days
WITH p, sum(weight * exp(-age_days / 260.0)) AS score, collect(DISTINCT pr.url)[..5] AS evidence
RETURN p.login AS person, round(score * 10) / 10 AS score, evidence
ORDER BY score DESC
LIMIT 5
```

The full query reference for all six tools lives in [cypher-queries.md](cypher-queries.md), written during implementation.

## Decision-candidate filter

A thread goes to the extraction model only if it matches at least one of:

- a merged PR with ≥ 3 review comments, **or** a linked issue;
- a closed issue with ≥ 3 comments;
- a PR that modifies a docs file (`is_doc = true`).

Everything else stays deterministic structure with no LLM cost.
