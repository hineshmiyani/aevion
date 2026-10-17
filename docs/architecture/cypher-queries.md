# Cypher query reference

Every query the product depends on, as the hackathon rules require (Rule 10). Each tool's source of truth is its module in `apps/api/src/aevion/tools/`; update this file **in the same PR** as any query change.

All tools read through `OrgGraph.ro_query` (`GRAPH.RO_QUERY`), so FalkorDB rejects any write. Every tool returns a `ToolResult` with an **evidence path**: the nodes and edges behind the answer, each of which exists in the graph (checked by `missing_edges()` in the tests).

## `experts_for`: who knows a Component? (US-1)

Module: `tools/experts.py` · API: `POST /api/tools/experts_for` `{org, component, repo?, limit?}`

**Scoring** (design constants, explainable in one sentence each):

| Signal | Weight |
|---|---|
| Authored a merged PR touching the Component | 3.0 |
| Reviewed such a PR (not their own) | 2.0 |
| Commented on such a PR | 0.5 |
| Recency | × `exp(-age_days / 260)`: a contribution ~180 days old counts half |

Bots never score. Unmerged PRs don't count.

**1. Resolve the Component** from an exact key or a path fragment:

```cypher
MATCH (c:Component)
WHERE (c.key = $component OR toLower(c.path_prefix) CONTAINS toLower($component))
  AND ($repo IS NULL OR c.repo = $repo)
RETURN c.key, c.name, c.repo
ORDER BY c.key = $component DESC, size(c.path_prefix)
LIMIT 5
```

**2. Score merged-PR authorship and reviews** (multi-hop: Component ← File ← PullRequest ← Person):

```cypher
MATCH (c:Component)<-[:IN_COMPONENT]-(f:File)<-[:MODIFIES]-(pr:PullRequest)
WHERE c.key IN $components AND pr.merged_at IS NOT NULL
MATCH (p:Person)-[r:AUTHORED|REVIEWED]->(pr)
WHERE NOT p.is_bot
WITH p, pr, type(r) AS role, collect(f.key)[0] AS file, collect(c.key)[0] AS component,
     exp(-((timestamp() - pr.merged_at) / 86400000.0) / $decay) AS recency
RETURN p.login AS login, pr.key AS pr, pr.title AS title, pr.url AS url, pr.merged_at AS at,
       role, file, component,
       CASE role WHEN 'AUTHORED' THEN $authored ELSE $reviewed END * recency AS points
```

**3. Score comments** on those PRs:

```cypher
MATCH (c:Component)<-[:IN_COMPONENT]-(:File)<-[:MODIFIES]-(pr:PullRequest)
WHERE c.key IN $components AND pr.merged_at IS NOT NULL
MATCH (p:Person)-[:AUTHORED]->(cm:Comment)-[:ON]->(pr)
WHERE NOT p.is_bot
WITH DISTINCT p, cm, pr
RETURN p.login AS login, cm.id AS comment, cm.url AS url, pr.key AS pr,
       $comment * exp(-((timestamp() - cm.created_at) / 86400000.0) / $decay) AS points
```

Python sums the points per person and keeps each person's 3 strongest PRs as evidence: `Person -AUTHORED|REVIEWED-> PullRequest -MODIFIES-> File -IN_COMPONENT-> Component`.

**Measured:** 7–12 ms per call on the `falkordb-py` graph (446 nodes, 1,557 edges).

## Ingestion writes

The loader's `UNWIND … MERGE` statements live in `apps/api/src/aevion/ingest/loader.py`. They are idempotent by design: every node MERGEs on its key from [graph-model.md](graph-model.md), and `link_references()` creates FIXES/REFERENCES edges from stored key lists after all repos are loaded.
