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

## `area_history`: what's the history of a Component? (US-3)

Module: `tools/history.py` · API: `POST /api/tools/area_history` `{org, component, repo?, days?, limit?}`

Three reads over the same Components (resolved like `experts_for`):

**Recent merged PRs** touching the Component in the window:

```cypher
MATCH (c:Component)<-[:IN_COMPONENT]-(f:File)<-[:MODIFIES]-(pr:PullRequest)
WHERE c.key IN $components AND pr.merged_at >= $since
WITH pr, collect(f.key)[0] AS file, collect(c.key)[0] AS component
OPTIONAL MATCH (a:Person)-[:AUTHORED]->(pr)
RETURN pr.key AS key, pr.title AS title, pr.url AS url, pr.merged_at AS merged_at,
       a.login AS author, file, component
ORDER BY merged_at DESC
LIMIT $limit
```

**Open issues tied to that code**: fixed or referenced by PRs that touched it, in either direction. An issue linked to several PRs is listed once.

```cypher
MATCH (c:Component)<-[:IN_COMPONENT]-(f:File)<-[:MODIFIES]-(pr:PullRequest)
WHERE c.key IN $components
MATCH (pr)-[r:FIXES|REFERENCES]-(i:Issue)
WHERE i.state = 'OPEN'
WITH i, pr, r, f, c
RETURN DISTINCT i.key AS key, i.title AS title, i.url AS url, i.created_at AS created_at,
       pr.key AS via_pr, pr.title AS via_title, pr.url AS via_url, type(r) AS link,
       startNode(r) = pr AS from_pr, f.key AS file, c.key AS component
LIMIT $limit
```

**Most active people** in the window (bots excluded):

```cypher
MATCH (c:Component)<-[:IN_COMPONENT]-(:File)<-[:MODIFIES]-(pr:PullRequest)
WHERE c.key IN $components AND pr.merged_at >= $since
MATCH (p:Person)-[r:AUTHORED|REVIEWED]->(pr)
WHERE NOT p.is_bot
WITH p, count(DISTINCT CASE type(r) WHEN 'AUTHORED' THEN pr END) AS authored,
     count(DISTINCT CASE type(r) WHEN 'REVIEWED' THEN pr END) AS reviewed
RETURN p.login AS login, authored, reviewed
ORDER BY authored + reviewed DESC
LIMIT 5
```

## `related_work`: what else does this touch? (US-4)

Module: `tools/related.py` · API: `POST /api/tools/related_work` `{org, key, limit?}`

1. Find whether the key is a PR or an issue.
2. **Direct links** in both directions (`FIXES` / `REFERENCES`), via a `UNION` of outgoing and incoming matches.
3. **Files and Components touched**: by the PR itself, or by the PRs linked to an issue.
4. **Overlapping PRs**: other PRs changing the same files, open ones first. This is the "what might conflict" signal:

```cypher
UNWIND $files AS file_key
MATCH (f:File {key: file_key})<-[:MODIFIES]-(other:PullRequest)
WHERE NOT other.key IN $exclude
WITH other, collect(DISTINCT f.key) AS shared
RETURN other.key AS key, other.title AS title, other.url AS url, other.state AS state,
       other.merged_at AS merged_at, shared
ORDER BY other.state = 'OPEN' DESC, size(shared) DESC, coalesce(other.merged_at, 0) DESC
LIMIT $limit
```

## `catch_up`: what changed since a date? (US-5)

Module: `tools/catch_up.py` · API: `POST /api/tools/catch_up` `{org, since, component?, repo?, limit?}`

Merged PRs in scope (Component-scoped or whole repo), then the issues those PRs closed, then releases. Bot-authored PRs are counted separately and left out of highlights and "who drove it".

```cypher
MATCH (c:Component)<-[:IN_COMPONENT]-(:File)<-[:MODIFIES]-(pr:PullRequest)-[:IN_REPO]->(r:Repo)
WHERE c.key IN $components AND pr.merged_at >= $since
WITH DISTINCT pr, r
OPTIONAL MATCH (a:Person)-[:AUTHORED]->(pr)
RETURN pr.key AS key, pr.title AS title, pr.url AS url, pr.merged_at AS merged_at,
       a.login AS author, coalesce(a.is_bot, false) AS bot, r.full_name AS repo
ORDER BY merged_at DESC
```

```cypher
UNWIND $prs AS pr_key
MATCH (pr:PullRequest {key: pr_key})-[:FIXES]->(i:Issue)
WHERE i.closed_at >= $since
RETURN DISTINCT i.key AS key, i.title AS title, i.url AS url, i.closed_at AS closed_at,
       pr.key AS fixed_by
```

**Measured on the real graph** (20,422 nodes, 77,710 edges): `related_work` 19 ms, `catch_up` 9 ms, `area_history` under 100 ms.

## FalkorDB Cypher notes

- `ORDER BY` can't contain an aggregation directly (`ORDER BY count(x)` fails with "failed to map aggregation expression"); aggregate into an alias in `WITH`/`RETURN` and order by the alias.
- `GRAPH.RO_QUERY` fails on a graph that doesn't exist yet; `bootstrap()` creates every org graph first.

## Ingestion writes

The loader's `UNWIND … MERGE` statements live in `apps/api/src/aevion/ingest/loader.py`. They are idempotent by design: every node MERGEs on its key from [graph-model.md](graph-model.md), and `link_references()` creates FIXES/REFERENCES edges from stored key lists after all repos are loaded.
