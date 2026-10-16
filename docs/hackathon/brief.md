# Hackathon brief: Graph Hacks, Context for AI Agents

**Source:** https://www.wemakedevs.org/hackathons/falkordb (Overview, Rules, Schedule, Resources, FAQ pages). Summarised on 2026-10-17. If anything here conflicts with the site, the site wins.

## Key facts

| | |
|---|---|
| Organisers | WeMakeDevs, in collaboration with FalkorDB |
| Window | **Oct 15, 00:01 IST → Oct 18, 23:59 IST** |
| Submissions open | Oct 17, 01:03 IST |
| Team | Aevion (team code `TZDTA4`), 3 of 4 seats filled |
| Registrants | ~7,400 |
| Format | Online, solo or teams of up to 4 |

> ⚠️ Once we submit, the team can no longer change. Add a fourth member, if any, **before** submitting.

## The challenge, in one line

Build a working agent (or group of agents) with FalkorDB as its context layer. The graph must shape what the agent does: it follows connections, remembers, and shows the path behind each answer.

## Tracks and prizes

You can enter one, two or all three tracks; each has its own prize. Every member of a winning team gets the prize.

| Track | Focus | Prize |
|---|---|---|
| 01 Agents That Act on Connected Data | Multi-hop reasoning, graph queries and algorithms as agent tools, tool selection through MCP, actions based on the graph, explainable results | iPhone 18 Pro |
| 02 Agent Memory and Coordination | Episodic, semantic and procedural memory; persistent history; shared state and handoffs between agents; many simultaneous reads and writes; separate memory per user or tenant | PS5 with GTA VI |
| 03 Company Brain | Docs, tickets and chats in one graph; who owns and who knows what; tracing decisions to their source; keeping knowledge current; answers with clear sources | M6 Mac Mini |

**Side prizes:** best blog post about the project (AirPods 5, 1 winner). Every member of the top 50 teams gets a t-shirt.

## Rules that shape our design

1. **FalkorDB is mandatory and must do real work.** A graph drawn on top of ordinary storage doesn't count. If the product still works with FalkorDB removed, it fails.
2. **Data:** public, synthetic or our own only. Nothing login-protected, paywalled, personal or otherwise restricted.
3. **New work:** the main coding and design must start after kickoff. General libraries and templates may be reused.
4. **AI assistants are allowed, but their use must be disclosed.** Projects that are entirely AI-generated without meaningful team contribution may be rejected.
5. **We must understand everything we submit:** the graph model, the queries, the architecture and the technical decisions.
6. **Name every track we enter** when submitting.
7. Any FalkorDB deployment works: Docker, self-hosted, or FalkorDB Cloud. Any language or framework.

## Judging

No scoring rubric is published. Signals from the brief and rules:

- The graph is load-bearing, not decorative.
- Answers are explainable ("show the path behind an answer").
- A live deployment is preferred.
- The team can explain its own work.

## Resources

- Docs: https://docs.falkordb.com (Cypher: `/cypher`, algorithms: `/algorithms`)
- Run locally: `docker pull falkordb/falkordb:latest`
- Integrations: GraphRAG-SDK, QueryWeaver, MCP, Graphiti, Cognee, LangChain, LlamaIndex
- Graph algorithms built in: shortest path, PageRank, centrality, connected components, community detection
- Help: FalkorDB Discord, https://discord.com/invite/Y2mMT9VdMy
