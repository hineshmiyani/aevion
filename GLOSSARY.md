# Glossary

The domain language for Aevion. Use these terms exactly in code, docs, UI and the demo. When a new term settles, add it here.

| Term | Meaning | Avoid |
|---|---|---|
| **Org graph** | One FalkorDB graph holding everything Aevion knows about one GitHub organisation (for example `org:falkordb`; names are always lowercase). | "database", "tenant DB" |
| **Component** | A part of a repo that people can know about: a directory prefix (for example `src/execution_plan`), with GitHub labels mapped onto it. The X in "who knows X". | "module", "area", "topic" |
| **Expert** | A person ranked highly for a Component by the live expertise query: weighted, recent merged PRs they authored or reviewed. Expertise is computed at question time, never stored. | "owner" (that is CODEOWNERS) |
| **Owner** | A person listed for a Component in CODEOWNERS, with a validity time range. Different from Expert. | |
| **Decision** | A choice extracted from a PR or issue thread, with summary, rationale and alternatives, linked to the evidence comments and the people who made it. | "ADR" (those are our own docs) |
| **Evidence path** | The graph path returned with every answer, showing which nodes and edges produced it. Shown in the UI and the API response. | "sources", "citations" |
| **Hero question** | One of the five questions Aevion must answer brilliantly: who knows X, why was X decided, history of X, what else does this touch, catch me up on X. | |
| **Tool** | A fixed, parameterised Cypher query the agent can call (for example `experts_for`). Also exposed over MCP. | "function", "skill" |
| **Triage** | The Track 01 flow: for a new issue, find duplicates and the component, pick an expert, draft a reply, and (on the sandbox only) apply the actions. | |
| **Sandbox** | `hineshmiyani/aevion-sandbox`, the only repo the agent may write to. | "test repo" |
| **Dry run** | Triage on a real FalkorDB issue that shows proposed actions without performing them. | |
| **Decision candidate** | A thread that passes the cheap filter and is sent for LLM extraction. | |
