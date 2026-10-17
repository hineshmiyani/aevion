// POST /api/triage: forwards to the Aevion API (AEVION_API_URL, read at request time), or
// serves a recorded dry run when no API is configured.
import { apiBase, visitorHeaders } from "@/lib/proxy";
import sample from "@/lib/triage-sample.json";
import type { AskFailure, TriageRequest, TriageResponse } from "@/lib/types";

const DEFAULT_ORG = "FalkorDB";
const UPSTREAM_TIMEOUT_MS = 90_000; // an apply on the sandbox also writes to GitHub
const ISSUE_KEY = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+#[0-9]+$/;

function failure(status: number, error: string, retryAfterSeconds?: number) {
  const body: AskFailure = { error, retryAfterSeconds };
  return Response.json(body, {
    status,
    headers: retryAfterSeconds ? { "Retry-After": String(retryAfterSeconds) } : undefined,
  });
}

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as Partial<TriageRequest> | null;
  const issueKey = body?.issue_key?.trim();
  if (!issueKey || !ISSUE_KEY.test(issueKey)) {
    return failure(400, "Use an issue key like FalkorDB/FalkorDB#3357.");
  }
  const mode = body?.mode === "apply" ? "apply" : "dry_run";

  const api = apiBase();
  if (!api) {
    await new Promise((resolve) => setTimeout(resolve, 700));
    return Response.json({ ...(sample as unknown as TriageResponse), sample: true });
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${api}/api/triage`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...visitorHeaders(request) },
      body: JSON.stringify({ org: body?.org ?? DEFAULT_ORG, issue_key: issueKey, mode }),
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
      cache: "no-store",
    });
  } catch {
    return failure(502, "The Aevion API didn't respond. Try again in a moment.");
  }

  if (upstream.status === 429) {
    const retry = Number(upstream.headers.get("Retry-After")) || 60;
    return failure(429, "You've run a lot of triages. Take a short break.", retry);
  }
  if (!upstream.ok) {
    const detail = await upstream.json().catch(() => null);
    return failure(upstream.status, detail?.detail ?? "Something went wrong triaging that issue.");
  }
  return Response.json(await upstream.json());
}
