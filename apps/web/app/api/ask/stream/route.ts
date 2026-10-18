// POST /api/ask/stream: pipes the Aevion API's Server-Sent Events through (each real tool
// call, then the answer). Without an API it replays the recorded sample as a cached answer.
import { apiBase, visitorHeaders } from "@/lib/proxy";
import { sampleAnswer } from "@/lib/sample-answer";
import type { AskFailure, AskRequest } from "@/lib/types";

const DEFAULT_ORG = "FalkorDB";
const UPSTREAM_TIMEOUT_MS = 90_000;

function failure(status: number, error: string, retryAfterSeconds?: number) {
  const body: AskFailure = { error, retryAfterSeconds };
  return Response.json(body, {
    status,
    headers: retryAfterSeconds ? { "Retry-After": String(retryAfterSeconds) } : undefined,
  });
}

const sse = (event: unknown) => `data: ${JSON.stringify(event)}\n\n`;

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as Partial<AskRequest> | null;
  const question = body?.question?.trim();
  if (!question) return failure(400, "Ask a question first.");
  if (question.length > 500) return failure(400, "Keep questions under 500 characters.");

  const api = apiBase();
  if (!api) {
    const answer = { ...sampleAnswer(question), elapsed_ms: 9 };
    return new Response(sse({ type: "cached" }) + sse({ type: "answer", answer }), {
      headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-store" },
    });
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${api}/api/ask/stream`, {
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
  if (!upstream.ok || !upstream.body) {
    const detail = await upstream.json().catch(() => null);
    return failure(upstream.status, detail?.detail ?? "Something went wrong answering that.");
  }
  return new Response(upstream.body, {
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-store", "X-Accel-Buffering": "no" },
  });
}
