"use client";

import { useCallback, useRef, useState } from "react";

import type { AskFailure, AskResponse, StreamEvent } from "@/lib/types";

/** One line of the progress log: a real step the agent took. */
export type Step =
  | { kind: "tool"; tool: string; args: Record<string, unknown>; rows?: number; ms?: number; done: boolean }
  | { kind: "writing"; done: boolean }
  | { kind: "cached" };

export type AskState =
  | { status: "idle" }
  | { status: "working"; question: string; steps: Step[] }
  | { status: "success"; question: string; steps: Step[]; data: AskResponse }
  | { status: "error"; question: string; steps: Step[]; error: string; retryAfterSeconds?: number };

function apply(steps: Step[], event: StreamEvent): Step[] {
  const settled = steps.map((s) => (s.kind === "writing" ? { ...s, done: true } : s));
  switch (event.type) {
    case "cached":
      return [...settled, { kind: "cached" }];
    case "tool":
      return [...settled, { kind: "tool", tool: event.tool, args: event.args, done: false }];
    case "tool_done": {
      const i = settled.findLastIndex((s) => s.kind === "tool" && s.tool === event.tool && !s.done);
      if (i === -1) return settled;
      const copy = [...settled];
      copy[i] = { ...(copy[i] as Extract<Step, { kind: "tool" }>), rows: event.rows, ms: event.ms, done: true };
      return copy;
    }
    case "writing":
      return [...settled, { kind: "writing", done: false }];
    default:
      return settled;
  }
}

/** Ask Aevion and follow its work live. A new question cancels the one in flight. */
export function useAskStream(org: string, initial?: { question: string; data: AskResponse }) {
  const [state, setState] = useState<AskState>(
    initial ? { status: "success", question: initial.question, steps: [{ kind: "cached" }], data: initial.data } : { status: "idle" },
  );
  const inFlight = useRef<AbortController | null>(null);

  const show = useCallback((question: string, data: AskResponse) => {
    inFlight.current?.abort();
    setState({ status: "success", question, steps: [{ kind: "cached" }], data });
  }, []);

  const ask = useCallback(
    async (question: string) => {
      inFlight.current?.abort();
      const controller = new AbortController();
      inFlight.current = controller;
      let steps: Step[] = [];
      setState({ status: "working", question, steps });
      const fail = (error: string, retryAfterSeconds?: number) =>
        setState({ status: "error", question, steps, error, retryAfterSeconds });

      try {
        const response = await fetch("/api/ask/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ org, question }),
          signal: controller.signal,
        });
        if (!response.ok || !response.body) {
          const failure = (await response.json().catch(() => ({}))) as Partial<AskFailure>;
          return fail(failure.error ?? "Something went wrong answering that.", failure.retryAfterSeconds);
        }
        const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
        let buffer = "";
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += value;
          const chunks = buffer.split("\n\n");
          buffer = chunks.pop() ?? "";
          for (const chunk of chunks) {
            const line = chunk.split("\n").find((l) => l.startsWith("data: "));
            if (!line) continue;
            const event = JSON.parse(line.slice(6)) as StreamEvent;
            if (event.type === "answer") {
              steps = steps.map((s) => (s.kind === "writing" ? { ...s, done: true } : s));
              setState({ status: "success", question, steps, data: event.answer });
              return;
            }
            if (event.type === "error") return fail(event.detail);
            steps = apply(steps, event);
            setState({ status: "working", question, steps });
          }
        }
        fail("The answer stopped before it finished. Ask again.");
      } catch {
        if (controller.signal.aborted) return;
        fail("Couldn't reach Aevion. Check your connection.");
      }
    },
    [org],
  );

  const reset = useCallback(() => {
    inFlight.current?.abort();
    inFlight.current = null;
    setState({ status: "idle" });
  }, []);

  return { state, ask, show, reset };
}
