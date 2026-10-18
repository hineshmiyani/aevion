"use client";

import { useMemo } from "react";

import type { Citation, EvidencePath } from "@/lib/types";

import { NODE_TYPE_NAMES, NodeGlyph } from "./NodeGlyph";

// Edge types read as short verbs on the rail.
const EDGE_VERBS: Record<string, string> = {
  AUTHORED: "authored",
  REVIEWED: "reviewed",
  MODIFIES: "changes",
  IN_COMPONENT: "in component",
  FIXES: "fixes",
  REFERENCES: "references",
  INCLUDES: "includes",
  DECIDED_IN: "decided in",
  EVIDENCED_BY: "evidenced by",
  MADE_BY: "made by",
  AFFECTS: "affects",
  SUPERSEDES: "supersedes",
  ON: "on",
  OWNS: "owns",
};

type Stop = { id: string; depth: number; via: string | null };

/** Walk the evidence path as a forest: start at nodes nothing points to, follow edges.
 * Roots that lead to the answer's first citations come first, so the trail opens with what
 * the answer actually cites rather than, say, a later Decision that superseded it. */
function trailStops(evidence: EvidencePath, citedOrder: Map<string, number>): Stop[] {
  const out = new Map<string, { target: string; type: string }[]>();
  const hasIncoming = new Set<string>();
  for (const e of evidence.edges) {
    out.set(e.source, [...(out.get(e.source) ?? []), { target: e.target, type: e.type }]);
    hasIncoming.add(e.target);
  }
  const firstCitation = (root: string) => {
    let best = Infinity;
    const seen = new Set<string>();
    const walk = (id: string) => {
      if (seen.has(id)) return;
      seen.add(id);
      best = Math.min(best, citedOrder.get(id) ?? Infinity);
      for (const edge of out.get(id) ?? []) walk(edge.target);
    };
    walk(root);
    return best;
  };
  const roots = evidence.nodes
    .filter((n) => !hasIncoming.has(n.id) && out.has(n.id))
    .map((n) => ({ n, first: firstCitation(n.id) }))
    .sort((a, b) => a.first - b.first)
    .map(({ n }) => n);
  const seen = new Set<string>();
  const stops: Stop[] = [];
  const visit = (id: string, depth: number, via: string | null) => {
    if (seen.has(id)) return;
    seen.add(id);
    stops.push({ id, depth, via });
    for (const edge of out.get(id) ?? []) visit(edge.target, depth + 1, edge.type);
  };
  roots.forEach((root) => visit(root.id, 0, null));
  // Anything unreachable from a root (isolated nodes) still appears, at the top level.
  evidence.nodes.forEach((n) => visit(n.id, 0, null));
  return stops;
}

type EvidenceTrailProps = {
  evidence: EvidencePath;
  citations: Citation[];
  highlighted: string | null;
};

export function EvidenceTrail({ evidence, citations, highlighted }: EvidenceTrailProps) {
  const citedAs = useMemo(() => new Map(citations.map((c) => [c.node_id, c.n])), [citations]);
  const stops = useMemo(() => trailStops(evidence, citedAs), [evidence, citedAs]);
  const nodes = useMemo(() => new Map(evidence.nodes.map((n) => [n.id, n])), [evidence]);

  if (stops.length === 0) {
    return <p className="text-sm text-muted">This answer didn&apos;t need graph evidence.</p>;
  }

  return (
    <ol className="relative" aria-label="Evidence path through the graph">
      {stops.map(({ id, depth, via }) => {
        const node = nodes.get(id);
        if (!node) return null;
        const n = citedAs.get(id);
        const lit = highlighted === id;
        return (
          <li
            key={id}
            id={`trail-${id}`}
            className="relative"
            style={{ paddingLeft: `${depth * 14}px` }}
          >
            {via && (
              <span className="flex items-center gap-2 py-0.5 pl-[6px] text-[11px] text-muted">
                <span aria-hidden className={`h-3 w-px ${lit ? "bg-path" : "bg-rule-strong"}`} />
                {EDGE_VERBS[via] ?? via.toLowerCase()}
              </span>
            )}
            <div
              className={`flex items-start gap-2 rounded-sm px-1 py-1 transition-colors duration-300 ${lit ? "bg-path-soft" : ""}`}
            >
              <NodeGlyph label={node.label} className="mt-[3px]" />
              <div className="min-w-0 flex-1 text-sm leading-snug">
                <span className="sr-only">{NODE_TYPE_NAMES[node.label] ?? node.label}: </span>
                {node.url ? (
                  <a
                    href={node.url}
                    target="_blank"
                    rel="noreferrer"
                    className="break-words text-ink underline decoration-rule-strong underline-offset-2 hover:decoration-path"
                  >
                    {node.title}
                  </a>
                ) : (
                  <span className="break-words">{node.title}</span>
                )}
              </div>
              {n !== undefined && (
                <span className={`mt-px shrink-0 text-xs tabular-nums ${lit ? "font-semibold text-path" : "text-muted"}`}>
                  {n}
                </span>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
