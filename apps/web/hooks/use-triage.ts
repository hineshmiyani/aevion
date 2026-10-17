"use client";

import { useCallback, useRef, useState } from "react";

import type { AskFailure, TriageMode, TriageResponse } from "@/lib/types";

export type TriageState =
  | { status: "idle" }
  | { status: "loading"; issueKey: string; mode: TriageMode }
  | { status: "success"; issueKey: string; data: TriageResponse }
  | { status: "error"; issueKey: string; error: string; retryAfterSeconds?: number };

/** Triage one issue. A new request cancels the one in flight. */
export function useTriage(org: string) {
  const [state, setState] = useState<TriageState>({ status: "idle" });
  const inFlight = useRef<AbortController | null>(null);

  const triage = useCallback(
    async (issueKey: string, mode: TriageMode) => {
      inFlight.current?.abort();
      const controller = new AbortController();
      inFlight.current = controller;
      setState({ status: "loading", issueKey, mode });
      try {
        const response = await fetch("/api/triage", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ org, issue_key: issueKey, mode }),
          signal: controller.signal,
        });
        const body = (await response.json()) as TriageResponse | AskFailure;
        if (!response.ok || "error" in body) {
          const failure = body as AskFailure;
          setState({
            status: "error",
            issueKey,
            error: failure.error ?? "Something went wrong triaging that issue.",
            retryAfterSeconds: failure.retryAfterSeconds,
          });
          return;
        }
        setState({ status: "success", issueKey, data: body });
      } catch {
        if (controller.signal.aborted) return;
        setState({ status: "error", issueKey, error: "Couldn't reach Aevion. Check your connection." });
      }
    },
    [org],
  );

  return { state, triage };
}
