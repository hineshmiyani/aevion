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

## `decision_trail`: why was X decided? (US-2)

Module: `tools/decisions.py` · API: `POST /api/tools/decision_trail` `{org, topic?, component?, repo?, limit?}`

**Find decisions** by full-text search over `Decision(summary, rationale)`. The topic is reduced to keywords joined with `|` (OR); FalkorDB's index stems words, so "queues" matches "queue". Optionally keep only decisions that `AFFECTS` the given Components:

```cypher
CALL db.idx.fulltext.queryNodes('Decision', $query) YIELD node, score
OPTIONAL MATCH (node)-[:AFFECTS]->(c:Component)
WITH node, score, collect(c.key) AS affects
WHERE size($components) = 0 OR any(k IN affects WHERE k IN $components)
RETURN node.id AS id, score, node.confidence AS confidence,
       node.summary + ' ' + node.rationale AS text
ORDER BY score DESC
LIMIT $pool
```

**Re-rank the pool (50 candidates) in Python.** The index's TF-IDF score rewards short text that repeats one query word: for "Why did FalkorDB gate main on a merge queue?" it ranked *"CI jobs set timeouts and merge queue entries are not cancelled"* above *"Gate main with a merge queue…"*. So candidates are ordered by **keyword coverage** (the share of the question's distinct keywords, lightly stemmed, that the decision contains), then by `score × confidence`. FalkorDB still does the finding; Python only orders a small pool. Measured on the real graph (534 decisions): 8–20 ms.

**Walk each decision's trail**: thread, the issues it fixed, people, Components:

```cypher
MATCH (d:Decision {id: $id})-[:DECIDED_IN]->(t)
OPTIONAL MATCH (t)-[:FIXES]->(fixed:Issue)
OPTIONAL MATCH (d)-[:MADE_BY]->(p:Person)
OPTIONAL MATCH (d)-[:AFFECTS]->(c:Component)
RETURN d.summary AS summary, d.rationale AS rationale, d.alternatives AS alternatives,
       d.decided_at AS decided_at, d.confidence AS confidence,
       labels(t)[0] AS thread_label, t.key AS thread_key, t.title AS thread_title,
       t.url AS thread_url,
       collect(DISTINCT [fixed.key, fixed.title, fixed.url]) AS fixed,
       collect(DISTINCT p.login) AS made_by,
       collect(DISTINCT [c.key, c.name]) AS components
```

…plus up to 4 evidence comments (`EVIDENCED_BY`) with their authors, and the `SUPERSEDES` chain in both directions.

### How `SUPERSEDES` is created

After each extraction run, `link_supersedes()` links a newer decision to an older one only when both affect the same Component **and** the newer decision's thread links to the older one's within two `REFERENCES`/`FIXES` hops. It's evidence-based and deterministic: no LLM call, nothing guessed.

```cypher
MATCH (new:Decision)-[:DECIDED_IN]->(nt), (old:Decision)-[:DECIDED_IN]->(ot)
WHERE new <> old AND new.decided_at > old.decided_at AND nt <> ot
MATCH (new)-[:AFFECTS]->(c:Component)<-[:AFFECTS]-(old)
MATCH (nt)-[:REFERENCES|FIXES*1..2]-(ot)
WITH DISTINCT new, old
MERGE (new)-[s:SUPERSEDES]->(old)
SET s.at = new.decided_at
```

## `triage_candidates`: what is this issue about, and who should look? (US-6)

Module: `tools/triage.py` · API: `POST /api/tools/triage_candidates` `{org, issue, limit?}`, and `POST /api/triage` `{org, issue_key, mode}` (`triage/service.py`)

A new issue has no edges of its own yet, so the graph answers **by analogy**: issues like this one, the code that fixed them, and the people who know that code.

**1. Similar issues.** Full-text candidates from the issue title's keywords, then re-ranked in Python by title coverage (as in `decision_trail`). A title coverage of 0.6 or more marks a *likely duplicate*:

```cypher
CALL db.idx.fulltext.queryNodes('Issue', $query) YIELD node, score
WITH node, score WHERE node.key <> $key
MATCH (node)-[:IN_REPO]->(r:Repo)
OPTIONAL MATCH (pr:PullRequest)-[:FIXES]->(node)
RETURN node.key AS key, node.title AS title, node.body_excerpt AS body, node.state AS state,
       node.url AS url, r.full_name AS repo, score, collect(pr.key) AS fixed_by
ORDER BY score DESC
LIMIT $pool
```

**2. Component votes.** The Components that the similar issues' fixing PRs changed. A PR's vote is split across the Components it touched (weight / √n), so a focused fix counts for more than a sweeping refactor. Tests, CI, build, docs and root folders never vote, and only the issue's own repo can win:

```cypher
UNWIND $issues AS issue_key
MATCH (i:Issue {key: issue_key})<-[:FIXES]-(pr:PullRequest)-[:MODIFIES]->(f:File)
      -[:IN_COMPONENT]->(c:Component)
WHERE NOT f.is_doc
RETURN issue_key AS issue, pr.key AS pr, pr.title AS pr_title, pr.url AS pr_url,
       f.key AS file, f.path AS path, c.key AS component, c.name AS name
LIMIT 600
```

Two more votes: files the issue names (`op_merge.c`, `src/graph/graph.c`) matched to real `File` nodes, and Components whose path words match the title's keywords ("UDF" → `src/udf`). Path words in more than 10% of a repo's Components (like `graph` in FalkorDB) are too common to vote:

```cypher
UNWIND $paths AS mentioned
MATCH (f:File)-[:IN_COMPONENT]->(c:Component)
WHERE f.repo = $repo AND (f.path = mentioned OR f.path ENDS WITH ('/' + mentioned))
RETURN mentioned, f.key AS file, f.path AS path, c.key AS component, c.name AS name
LIMIT 20
```

Each pick gets a **strength** (strong ≥ 1.0 votes, moderate ≥ 0.4, else weak). A weak pick isn't proposed as a label, and the draft reply says the area is a guess.

**3. Expert.** `experts_for` on the winning Component, minus the issue's author.

**The reply never pings anyone** ([ADR-0013](../adr/0013-triage-never-pings-real-people.md)): the Expert is a real FalkorDB maintainer, so they're named as a profile link, `@login` in model output is defused, and bare `#123` references are linked to the item meant (or escaped), because on the sandbox they would autolink to the wrong issue.

**Measured on the real graph:** the tool runs in about 1 s; a full dry run with the drafted reply in 4 to 6 s.

## Sandbox triage: webhook in, actions out (US-6, AEV-32)

Modules: `api/routes/webhooks.py`, `sandbox/apply.py` · `POST /webhooks/github` (HMAC-verified), and `POST /api/triage` with `mode: "apply"` on a sandbox issue.

1. **Ingest** the webhook's issue (and comment, for `issue_comment`) into `org:aevion-sandbox` with the same `UNWIND … MERGE` loader as ingestion: the REST payload is reshaped into the GraphQL record shape first.
2. **Reason on `org:falkordb`**: `triage_issue()` is `triage_candidates` from the issue's text instead of a stored key. A seeded copy is triaged in its original's repo (read from its hidden marker); a freshly typed issue against `FalkorDB/FalkorDB`.
3. **Act** through `SandboxWriter` only: the label (`area: <component>`, created on first use), assign if the Expert is a sandbox collaborator (otherwise named by profile link), and the reply, made safe by `safe_for_sandbox`.
4. **Record** the run, so the same issue is never answered twice:

```cypher
MATCH (i:Issue {key: $key})
MERGE (t:TriageRun {issue_key: $key})
SET t.at = $at, t.result = $result
MERGE (t)-[:FOR]->(i)
```

Only `issues.opened` triggers a triage; edits, closes and comments are ingested only, so Aevion's own comment can't trigger another run. **Measured:** filing a real sandbox issue to label and comment took 10.5 s (SPEC target: 30 s).

**Webhook setup** (on deploy, AEV-14): in the sandbox repo's Settings → Webhooks, payload URL `https://<api-host>/webhooks/github`, content type `application/json`, the `GITHUB_WEBHOOK_SECRET` from the API's environment, and the events *Issues* and *Issue comments*.

## FalkorDB Cypher notes

- `ORDER BY` can't contain an aggregation directly (`ORDER BY count(x)` fails with "failed to map aggregation expression"); aggregate into an alias in `WITH`/`RETURN` and order by the alias.
- `GRAPH.RO_QUERY` fails on a graph that doesn't exist yet; `bootstrap()` creates every org graph first.
- `x ENDS WITH '/' + y` parses as `(x ENDS WITH '/') + y` and fails with "Type mismatch: expected Boolean but was String". Parenthesise the concatenation: `x ENDS WITH ('/' + y)`.

## Ingestion writes

The loader's `UNWIND … MERGE` statements live in `apps/api/src/aevion/ingest/loader.py`. They are idempotent by design: every node MERGEs on its key from [graph-model.md](graph-model.md), and `link_references()` creates FIXES/REFERENCES edges from stored key lists after all repos are loaded.
