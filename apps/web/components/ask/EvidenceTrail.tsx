"use client";

import { useMemo } from "react";

import type { Citation, EvidencePath } from "@/lib/types";

import { GitHubMark } from "@/components/WorkspaceIcons";

import { NODE_TYPE_NAMES, NodeGlyph } from "./NodeGlyph";

// Edge types read as short verbs on the rail.
export const EDGE_VERBS: Record<string, string> = {
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
  IN_REPO: "in repo",
  HAS_LABEL: "labelled",
  ASSIGNED_TO: "assigned to",
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

type Guide = "pass" | "none" | "tee" | "elbow";

/** File-tree guides: a line keeps running at a level while a later row still hangs off it. */
function treeGuides(stops: Stop[]): Guide[][] {
  return stops.map(({ depth }, i) => {
    const continues = (level: number) => {
      for (let j = i + 1; j < stops.length; j++) {
        if (stops[j].depth < level) return false;
        if (stops[j].depth === level) return true;
      }
      return false;
    };
    return Array.from({ length: depth }, (_, k) => {
      const level = k + 1;
      if (level === depth) return continues(level) ? "tee" : "elbow";
      return continues(level) ? "pass" : "none";
    });
  });
}

type EvidenceTrailProps = {
  evidence: EvidencePath;
  citations: Citation[];
  highlighted: string | null;
  onSelect?: (id: string) => void;
  /** Hovering a title lights its node on the map. */
  onHover?: (id: string | null) => void;
};

export function EvidenceTrail({ evidence, citations, highlighted, onSelect, onHover }: EvidenceTrailProps) {
  const citedAs = useMemo(() => new Map(citations.map((c) => [c.node_id, c.n])), [citations]);
  const stops = useMemo(() => trailStops(evidence, citedAs), [evidence, citedAs]);
  const guides = useMemo(() => treeGuides(stops), [stops]);
  const nodes = useMemo(() => new Map(evidence.nodes.map((n) => [n.id, n])), [evidence]);

  if (stops.length === 0) {
    return <p className="text-sm text-muted">This answer didn&apos;t need graph evidence.</p>;
  }

  return (
    <ol className="trail" aria-label="Evidence path through the graph">
      {stops.map(({ id, via }, i) => {
        const node = nodes.get(id);
        if (!node) return null;
        const lit = highlighted === id;
        const type = NODE_TYPE_NAMES[node.label] ?? node.label;
        const verb = via ? EDGE_VERBS[via] ?? via.toLowerCase().replaceAll("_", " ") : null;
        return (
          <li key={id} id={`trail-${id}`} className={`trail-item ${lit ? "is-lit" : ""} ${stops[i].depth === 0 ? "is-root" : ""}`}>
            {guides[i].map((guide, k) => <span key={k} className={`trail-guide is-${guide}`} aria-hidden="true" />)}
            <div className="trail-row">
              <span className="trail-glyph"><NodeGlyph label={node.label} /></span>
              <div className="trail-text">
                {verb && <span className="trail-via" aria-hidden="true">{verb}</span>}
                <div className="trail-main">
                  {/* Only the words link to the map, so the row's empty space stays inert. */}
                  {onSelect
                    ? <button type="button" className="trail-title" aria-pressed={lit} aria-label={`Show ${node.title} on map`} onClick={() => onSelect(id)}
                        onMouseEnter={() => onHover?.(id)} onMouseLeave={() => onHover?.(null)} onFocus={() => onHover?.(id)} onBlur={() => onHover?.(null)}>
                        <span>{node.title}</span>
                      </button>
                    : <span className="trail-title"><span className="sr-only">{verb ? `${verb}, ` : ""}{type}: </span><span>{node.title}</span></span>}
                  {node.url && <a className="trail-gh" href={node.url} target="_blank" rel="noreferrer" aria-label={`Open ${node.title} on GitHub`}><GitHubMark /><span aria-hidden="true">GitHub</span></a>}
                </div>
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
