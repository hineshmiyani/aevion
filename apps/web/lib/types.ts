// Types for the Aevion API. Tool shapes are generated from FastAPI's OpenAPI schema
// (`pnpm gen:api`); the /api/ask response mirrors docs/product/SPEC.md section 8.
import type { components } from "./api-schema";

// Pydantic list fields with defaults appear optional in OpenAPI; the API always sends them.
export type EvidencePath = Required<components["schemas"]["EvidencePath"]>;
export type EvidenceNode = components["schemas"]["EvidenceNode"];
export type EvidenceEdge = components["schemas"]["EvidenceEdge"];
export type ToolResult = Omit<components["schemas"]["ToolResult"], "evidence"> & { evidence: EvidencePath };

export type ToolCall = { tool: string; args: Record<string, unknown> };

/** `[n]` in the answer text points at evidence node `node_id`. */
export type Citation = { n: number; node_id: string };

export type AskResponse = {
  answer: string;
  citations: Citation[];
  tool_calls: ToolCall[];
  evidence: EvidencePath;
  cypher: string[];
  model: string;
  cached: boolean;
  elapsed_ms?: number | null; // server time to answer
  sample?: boolean; // true when served by the web app's built-in sample (no API configured)
};

export type AskRequest = { org: string; question: string };

export type AskFailure = { error: string; retryAfterSeconds?: number };

// Triage (/api/triage). The API's dict fields are untyped in OpenAPI; these are their shapes,
// as built by apps/api/src/aevion/tools/triage.py and triage/service.py.
export type TriageMode = components["schemas"]["TriageRequest"]["mode"];
export type TriageAction = components["schemas"]["TriageAction"];

export type TriageIssue = {
  key: string;
  title: string;
  state: string;
  url: string;
  repo: string;
  author: string | null;
  context_repo?: string; // sandbox issues: the repo whose code they were triaged against
  context_reason?: string[];
};

export type SimilarIssue = {
  key: string;
  title: string;
  state: string;
  url: string;
  repo: string;
  match: number; // share of this issue's title keywords the similar title covers
  fixed_by: string[];
  likely_duplicate: boolean;
};

export type ComponentPick = {
  key: string;
  name: string;
  votes: number;
  strength: "strong" | "moderate" | "weak";
  via: string[];
};

export type ExpertPick = {
  login: string;
  url: string;
  score: number;
  authored_prs: number;
  reviewed_prs: number;
  comments: number;
};

export type TriageResponse = {
  issue: TriageIssue;
  mode: TriageMode;
  duplicates: SimilarIssue[];
  related: SimilarIssue[];
  component: ComponentPick | null;
  expert: ExpertPick | null;
  draft_reply: string;
  actions: TriageAction[];
  evidence: EvidencePath;
  cypher: string[];
  model: string | null;
  sample?: boolean;
};

export type TriageRequest = { org: string; issue_key: string; mode: TriageMode };

// GET /api/stats (apps/api/src/aevion/api/routes/stats.py).
export type GraphStats = {
  org: string;
  nodes: number;
  edges: number;
  repos: number;
  people: number;
  pull_requests: number;
  issues: number;
  decisions: number;
  components: number;
  sample?: boolean;
};

// POST /api/ask/stream: Server-Sent Events, one JSON object per `data:` line.
export type StreamEvent =
  | { type: "cached" }
  | { type: "tool"; tool: string; args: Record<string, unknown> }
  | { type: "tool_done"; tool: string; rows: number; ms: number }
  | { type: "writing" }
  | { type: "answer"; answer: AskResponse & { elapsed_ms?: number | null } }
  | { type: "error"; status: number; detail: string };
