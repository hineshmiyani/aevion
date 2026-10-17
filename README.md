# Aevion: Company Brain on FalkorDB

> Team **Aevion**'s entry for [Graph Hacks: Context for AI Agents](https://www.wemakedevs.org/hackathons/falkordb) (WeMakeDevs × FalkorDB, Oct 15–18, 2026).

**Status:** design phase. Product, graph model and deployment are locked ([ADRs 0001–0012](docs/adr/), [graph model](docs/architecture/graph-model.md)). The [spec](docs/product/SPEC.md) is drafted and awaiting team approval; the implementation plan comes next.

## What we're building

An agent that understands how an open-source company works. It loads a GitHub organisation's public issues, PRs, reviews, commits and docs into a FalkorDB graph. It then answers questions like *"who knows this system?"* and *"why was this decided?"*, with the graph path behind every answer. It also triages incoming issues by acting on what the graph shows.

- **Tracks:** 03 Company Brain (main), 01 Agents That Act on Connected Data (secondary). See [ADR-0004](docs/adr/0004-product-scope-and-data.md).
- **Demo dataset:** the FalkorDB GitHub org.

## Where things live

| You want to… | Go to |
|---|---|
| Understand the hackathon rules and deadline | [docs/hackathon/brief.md](docs/hackathon/brief.md) |
| See what we must submit | [docs/hackathon/submission-checklist.md](docs/hackathon/submission-checklist.md) |
| Understand why we picked this idea | [docs/research/track-analysis.md](docs/research/track-analysis.md) |
| Weigh in on open design decisions | [docs/grilling/](docs/grilling/) |
| Read decisions we've locked | [docs/adr/](docs/adr/) |
| Learn our domain vocabulary | [GLOSSARY.md](GLOSSARY.md) |
| Pick up a task | [Aevion Tasks board (Notion)](https://app.notion.com/p/374521bfeac54306bed66e0764812cda) |
| Learn our branch and commit conventions | [CONTRIBUTING.md](CONTRIBUTING.md) |
| See the full docs map | [docs/README.md](docs/README.md) |

## Team

| Name | GitHub |
|---|---|
| Hinesh Miyani (lead) | [@hineshmiyani](https://github.com/hineshmiyani) |
| Jignesh Dabhi | [@zephyr2e1](https://github.com/zephyr2e1) |
| Jaydeep Prajapati | [@jaydeepprajapati123](https://github.com/jaydeepprajapati123) |

> Setup instructions, the graph data model and the Cypher query reference will be added here once implementation starts. The hackathon requires all three in the README.
