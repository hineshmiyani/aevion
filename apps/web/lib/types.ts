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
  sample?: boolean; // true when served by the web app's built-in sample (no API configured)
};

export type AskRequest = { org: string; question: string };

export type AskFailure = { error: string; retryAfterSeconds?: number };
