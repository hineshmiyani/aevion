"use client";

import { useCallback, useRef, useState } from "react";

import type { AskFailure, AskResponse } from "@/lib/types";

export type AskState =
  | { status: "idle" }
  | { status: "loading"; question: string }
  | { status: "success"; question: string; data: AskResponse }
  | { status: "error"; question: string; error: string; retryAfterSeconds?: number };

/** Ask Aevion a question. A new question cancels the one in flight. */
export function useAsk(org: string) {
  const [state, setState] = useState<AskState>({ status: "idle" });
  const inFlight = useRef<AbortController | null>(null);

  const ask = useCallback(
    async (question: string) => {
      inFlight.current?.abort();
      const controller = new AbortController();
      inFlight.current = controller;
      setState({ status: "loading", question });

      try {
        const response = await fetch("/api/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ org, question }),
          signal: controller.signal,
        });
        const body = (await response.json()) as AskResponse | AskFailure;
        if (!response.ok || "error" in body) {
          const failure = body as AskFailure;
          setState({
            status: "error",
            question,
            error: failure.error ?? "Something went wrong answering that.",
            retryAfterSeconds: failure.retryAfterSeconds,
          });
          return;
        }
        setState({ status: "success", question, data: body });
      } catch (error) {
        if (controller.signal.aborted) return;
        setState({
          status: "error",
          question,
          error: error instanceof Error && error.message ? "Couldn't reach Aevion. Check your connection." : "Unknown error.",
        });
      }
    },
    [org],
  );

  return { state, ask };
}
