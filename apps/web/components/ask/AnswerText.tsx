"use client";

import { Fragment, type ReactNode } from "react";

import type { Citation, EvidenceNode } from "@/lib/types";

type AnswerTextProps = {
  text: string;
  citations: Citation[];
  nodes: Map<string, EvidenceNode>;
  onCite: (nodeId: string) => void;
  highlighted: string | null;
};

// The agent writes plain text with **bold**, `code` and [n] citation markers. This small
// renderer can't inject HTML: everything becomes React text nodes.
// A marker keeps any punctuation right after it, so the two never wrap apart.
const TOKEN = /(\*\*[^*]+\*\*|`[^`]+`|\[\d+\][.,;:!?]?)/g;

export function AnswerText({ text, citations, nodes, onCite, highlighted }: AnswerTextProps) {
  const byNumber = new Map(citations.map((c) => [c.n, c.node_id]));

  const renderInline = (line: string): ReactNode[] =>
    line.split(TOKEN).map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={i} className="font-semibold">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <code key={i} className="rounded-sm bg-surface px-1 py-0.5 font-mono text-[0.8em]">
            {part.slice(1, -1)}
          </code>
        );
      }
      const marker = /^\[(\d+)\]([.,;:!?]?)$/.exec(part);
      if (marker) {
        const n = Number(marker[1]);
        const nodeId = byNumber.get(n);
        const node = nodeId ? nodes.get(nodeId) : undefined;
        if (!nodeId || !node) return <Fragment key={i}>{part}</Fragment>;
        const lit = highlighted === nodeId;
        return (
          <span key={i} className="whitespace-nowrap">
          <sup>
            <button
              type="button"
              onClick={() => onCite(nodeId)}
              aria-label={`Source ${n}: ${node.title}`}
              aria-pressed={lit}
              className={`relative mx-px rounded-sm px-0.5 font-sans text-[11px] leading-none font-medium tabular-nums transition-colors after:absolute after:-inset-1.5 after:content-[""] ${lit ? "bg-path text-paper" : "text-path hover:bg-path-soft"}`}
            >
              {n}
            </button>
          </sup>
          {marker[2]}
          </span>
        );
      }
      return <Fragment key={i}>{part}</Fragment>;
    });

  return (
    <div className="max-w-[68ch] space-y-4 font-serif text-[18px] leading-[1.7] text-ink">
      {text.split(/\n{2,}/).map((block, i) => {
        const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
        const items = lines.filter((line) => /^[-*] /.test(line));
        // A block of "- " lines is a list; a lead-in line before the items stays a paragraph.
        if (items.length > 0 && items.length >= lines.length - 1) {
          const lead = lines[0] && !/^[-*] /.test(lines[0]) ? lines[0] : null;
          return (
            <div key={i}>
              {lead && <p>{renderInline(lead)}</p>}
              <ul className="mt-2 list-disc space-y-1.5 pl-5 marker:text-muted">
                {items.map((item, j) => (
                  <li key={j}>{renderInline(item.slice(2))}</li>
                ))}
              </ul>
            </div>
          );
        }
        return <p key={i}>{renderInline(lines.join(" "))}</p>;
      })}
    </div>
  );
}
