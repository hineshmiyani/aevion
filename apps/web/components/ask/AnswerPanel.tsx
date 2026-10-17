"use client";

import { useMemo, useState } from "react";

import type { AskResponse } from "@/lib/types";

import { AnswerText } from "./AnswerText";
import { EvidenceTrail } from "./EvidenceTrail";

function describeCall(call: AskResponse["tool_calls"][number]) {
  const args = Object.entries(call.args)
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([key, value]) => `${key}=${JSON.stringify(value)}`)
    .join(", ");
  return `${call.tool}(${args})`;
}

/** A successful answer: prose with citations beside the evidence trail it came from. */
export function AnswerPanel({ question, data }: { question: string; data: AskResponse }) {
  const [highlighted, setHighlighted] = useState<string | null>(null);
  const nodes = useMemo(() => new Map(data.evidence.nodes.map((n) => [n.id, n])), [data]);

  const onCite = (nodeId: string) => {
    setHighlighted((current) => (current === nodeId ? null : nodeId));
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document
      .getElementById(`trail-${nodeId}`)
      ?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "nearest" });
  };

  return (
    <div className="grid gap-x-12 gap-y-10 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <article aria-labelledby="answer-question" className="min-w-0">
        <h2 id="answer-question" className="mb-5 font-serif text-xl leading-snug text-muted">
          {question}
        </h2>
        <AnswerText text={data.answer} citations={data.citations} nodes={nodes} onCite={onCite} highlighted={highlighted} />

        <details className="mt-8 border-t border-rule pt-3 text-sm text-muted">
          <summary className="cursor-pointer select-none hover:text-ink">
            How this was answered: {data.tool_calls.length} graph {data.tool_calls.length === 1 ? "query" : "queries"},{" "}
            {data.evidence.edges.length} edges traced
          </summary>
          <ul className="mt-2 space-y-1">
            {data.tool_calls.map((call, i) => (
              <li key={i}>
                <code className="font-mono text-xs text-ink">{describeCall(call)}</code>
              </li>
            ))}
          </ul>
        </details>

        {data.sample && (
          <p className="mt-4 text-xs text-muted">
            This is a recorded sample answer. Point the app at the Aevion API with AEVION_API_URL to ask live questions.
          </p>
        )}
      </article>

      <aside
        aria-labelledby="trail-heading"
        className="lg:sticky lg:top-8 lg:max-h-[calc(100vh-4rem)] lg:self-start lg:overflow-y-auto lg:border-l lg:border-rule lg:pl-6"
      >
        <h2 id="trail-heading" className="mb-3 text-sm font-medium">
          Where this comes from
        </h2>
        <EvidenceTrail evidence={data.evidence} citations={data.citations} highlighted={highlighted} />
      </aside>
    </div>
  );
}
