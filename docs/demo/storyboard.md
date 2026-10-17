# Demo video storyboard

**Shape:** "the judge's own org" hook ([grilling round 2](../grilling/round-02.md), Q11). **Length:** about 3 minutes. **Rule:** the graph is visibly doing work within the first 20 seconds.

| Time | Scene | What's on screen | Point it proves |
|---|---|---|---|
| 0:00–0:30 | **"Who knows FalkorDB's query planner?"** | Question typed into Aevion; ranked experts appear; the evidence path animates through PRs, reviews and files | Live multi-hop traversal; answers come with sources |
| 0:30–1:15 | **"Why was X decided?"** | Decision trail: Decision → PR → review comments → original issue → people; a superseded earlier decision is shown | Tracing decisions to their source; knowledge kept current over time |
| 1:15–2:00 | **Live triage** | An issue is filed in `aevion-sandbox`; the webhook updates the graph within seconds; the agent finds a duplicate, the component and an expert, then labels, assigns and comments | Track 01: an agent acting on what the graph shows |
| 2:00–2:30 | **Inside Claude Code via MCP** | The same tools called from Claude Code: "catch me up on GraphRAG-SDK since October 1" | Tool selection through MCP; ecosystem fit |
| 2:30–3:00 | **How it works** | Graph model diagram, one Cypher query on screen, architecture in one slide | The graph is load-bearing (Rule 3); the team can explain it (Rule 12) |

## Production notes

- Pre-compute the hero answers so recording doesn't depend on live LLM latency, but keep the triage scene live.
- Show real FalkorDB names and PR numbers. Double-check every on-screen answer against GitHub before recording.
- End card: repo URL, live URL, tracks entered (03 Company Brain, 01 Agents That Act).
