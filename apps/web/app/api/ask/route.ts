// POST /api/ask: forwards to the Aevion API (AEVION_API_URL, read at request time), or
// serves the built-in sample answer when no API is configured.
import { visitorHeaders } from "@/lib/proxy";
import { sampleAnswer } from "@/lib/sample-answer";
import type { AskFailure, AskRequest } from "@/lib/types";

const DEFAULT_ORG = "FalkorDB";
const UPSTREAM_TIMEOUT_MS = 60_000;

function failure(status: number, error: string, retryAfterSeconds?: number) {
  const body: AskFailure = { error, retryAfterSeconds };
  return Response.json(body, {
    status,
    headers: retryAfterSeconds ? { "Retry-After": String(retryAfterSeconds) } : undefined,
  });
}

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as Partial<AskRequest> | null;
  const question = body?.question?.trim();
  if (!question) return failure(400, "Ask a question first.");
  if (question.length > 500) return failure(400, "Keep questions under 500 characters.");

  const api = process.env.AEVION_API_URL;
  if (!api) {
    await new Promise((resolve) => setTimeout(resolve, 700)); // feel like a real round trip
    return Response.json(sampleAnswer(question));
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${api.replace(/\/$/, "")}/api/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...visitorHeaders(request) },
      body: JSON.stringify({ org: body?.org ?? DEFAULT_ORG, question }),
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
      cache: "no-store",
    });
  } catch {
    return failure(502, "The Aevion API didn't respond. Try again in a moment.");
  }

  if (upstream.status === 429) {
    const retry = Number(upstream.headers.get("Retry-After")) || 60;
    return failure(429, "You've asked a lot of questions. Take a short break.", retry);
  }
  if (!upstream.ok) {
    const detail = await upstream.json().catch(() => null);
    return failure(upstream.status, detail?.detail ?? "Something went wrong answering that.");
  }
  return Response.json(await upstream.json());
}
