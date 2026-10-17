"use client";

import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  type SimulationNodeDatum,
} from "d3-force";
import { useMemo, type KeyboardEvent } from "react";

import type { EvidenceNode, EvidencePath } from "@/lib/types";

import { NODE_SHAPES, NODE_TYPE_NAMES } from "./NodeGlyph";

const WIDTH = 720;
const HEIGHT = 380;
const GLYPH = 18; // px, drawn from the 14-unit glyph shapes
const LABELLED = new Set(["Person", "Component"]); // short names worth showing permanently

type Placed = EvidenceNode & SimulationNodeDatum & { x: number; y: number };
type Link = { source: string; target: string; type: string };

/** Lay the graph out once, synchronously: calm, deterministic, nothing moves. */
function layout(evidence: EvidencePath): { nodes: Placed[]; links: Link[]; viewBox: string; aspect: number } {
  const nodes = evidence.nodes.map((n) => ({ ...n })) as Placed[];
  const ids = new Set(nodes.map((n) => n.id));
  const links = evidence.edges.filter((e) => ids.has(e.source) && ids.has(e.target)).map((e) => ({ ...e }));
  const simulation = forceSimulation(nodes)
    .force("link", forceLink<Placed, { source: string | Placed; target: string | Placed }>(links.map((l) => ({ ...l }))).id((d) => d.id).distance(64))
    .force("charge", forceManyBody().strength(-260))
    .force("collide", forceCollide(22))
    .force("center", forceCenter(WIDTH / 2, HEIGHT / 2))
    // The frame is wide; pull harder vertically so the layout spreads sideways to fill it.
    .force("x", forceX(WIDTH / 2).strength(0.02))
    .force("y", forceY(HEIGHT / 2).strength(0.14))
    .stop();
  simulation.tick(300);

  const xs = nodes.map((n) => n.x);
  const ys = nodes.map((n) => n.y);
  // Permanent labels sit right of the glyph; ~6px per character at 11px keeps them inside the frame.
  const rights = nodes.map((n) => n.x + (LABELLED.has(n.label) ? GLYPH + Math.min(n.title.length, 34) * 6 : 0));
  const pad = 48;
  const minX = Math.min(...xs) - pad;
  const minY = Math.min(...ys) - pad;
  const width = Math.max(Math.max(...rights) + pad / 2 - minX, 240);
  const height = Math.max(Math.max(...ys) + pad - minY, 180);
  return { nodes, links, viewBox: `${minX} ${minY} ${width} ${height}`, aspect: width / height };
}

type EvidenceGraphProps = {
  evidence: EvidencePath;
  highlighted: string | null;
  onSelect: (nodeId: string) => void;
};

export function EvidenceGraph({ evidence, highlighted, onSelect }: EvidenceGraphProps) {
  const { nodes, links, viewBox, aspect } = useMemo(() => layout(evidence), [evidence]);
  const position = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);
  const selected = highlighted ? position.get(highlighted) : undefined;
  const neighbours = useMemo(() => {
    const set = new Set<string>();
    if (!highlighted) return set;
    for (const l of links) {
      if (l.source === highlighted) set.add(l.target);
      if (l.target === highlighted) set.add(l.source);
    }
    return set;
  }, [links, highlighted]);
  const typesShown = [...new Set(nodes.map((n) => n.label))];

  const onKey = (event: KeyboardEvent, id: string) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(id);
    }
  };

  return (
    <figure className="m-0">
      <svg
        viewBox={viewBox}
        role="group"
        aria-label={`Evidence graph: ${nodes.length} nodes and ${links.length} connections. The list beside the answer shows the same path.`}
        // Sized by the layout's own shape, so a phone shows the whole graph at full width, not a strip.
        style={{ aspectRatio: aspect }}
        className="max-h-[420px] w-full rounded-md border border-rule bg-surface"
      >
        <g aria-hidden>
          {links.map((l, i) => {
            const a = position.get(l.source);
            const b = position.get(l.target);
            if (!a || !b) return null;
            const lit = highlighted !== null && (l.source === highlighted || l.target === highlighted);
            return (
              <line
                key={i}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={lit ? "var(--path)" : "var(--rule-strong)"}
                strokeWidth={lit ? 2 : 1}
                strokeOpacity={highlighted && !lit ? 0.45 : 1}
              />
            );
          })}
        </g>
        {nodes.map((n) => {
          const isSelected = n.id === highlighted;
          const dimmed = highlighted !== null && !isSelected && !neighbours.has(n.id);
          const name = NODE_TYPE_NAMES[n.label] ?? n.label;
          return (
            <g
              key={n.id}
              role="button"
              tabIndex={0}
              aria-pressed={isSelected}
              aria-label={`${name}: ${n.title}`}
              onClick={() => onSelect(n.id)}
              onKeyDown={(e) => onKey(e, n.id)}
              transform={`translate(${n.x} ${n.y})`}
              className="cursor-pointer outline-none [&:focus-visible>circle.focus]:opacity-100"
              opacity={dimmed ? 0.35 : 1}
            >
              <circle className="focus opacity-0" r={GLYPH * 0.85} fill="none" stroke="var(--path)" strokeWidth={2} />
              {isSelected && <circle r={GLYPH * 0.75} fill="var(--path-soft)" stroke="var(--path)" strokeWidth={1.5} />}
              <g
                transform={`translate(${-GLYPH / 2} ${-GLYPH / 2}) scale(${GLYPH / 14})`}
                style={{ color: `var(--node-${n.label.toLowerCase()}, var(--muted))` }}
                fill={n.label === "Release" ? "none" : "currentColor"}
                stroke="currentColor"
                strokeWidth={n.label === "Release" ? 1.6 : 0}
              >
                {NODE_SHAPES[n.label] ?? <circle cx="7" cy="7" r="4" />}
              </g>
              {(LABELLED.has(n.label) || isSelected) && (
                <text
                  x={GLYPH * 0.75}
                  y={4}
                  className="fill-ink font-sans"
                  fontSize={11}
                  paintOrder="stroke"
                  stroke="var(--surface)"
                  strokeWidth={3}
                >
                  {n.title.length > 34 ? `${n.title.slice(0, 33)}…` : n.title}
                </text>
              )}
              <title>{`${name}: ${n.title}`}</title>
            </g>
          );
        })}
      </svg>

      <figcaption className="mt-3 flex flex-wrap items-start justify-between gap-x-6 gap-y-3 text-xs text-muted">
        <ul className="flex flex-wrap gap-x-4 gap-y-1" aria-label="Node types">
          {typesShown.map((label) => (
            <li key={label} className="flex items-center gap-1.5">
              <svg viewBox="0 0 14 14" width="12" height="12" aria-hidden style={{ color: `var(--node-${label.toLowerCase()}, var(--muted))` }} fill={label === "Release" ? "none" : "currentColor"} stroke="currentColor" strokeWidth={label === "Release" ? 1.6 : 0}>
                {NODE_SHAPES[label]}
              </svg>
              {NODE_TYPE_NAMES[label] ?? label}
            </li>
          ))}
        </ul>
        <p aria-live="polite" className="min-h-4 max-w-md text-right">
          {selected ? (
            <>
              <span className="text-ink">{selected.title}</span>
              {selected.url && (
                <>
                  {" "}
                  <a href={selected.url} target="_blank" rel="noreferrer" className="text-path underline underline-offset-2">
                    Open on GitHub
                  </a>
                </>
              )}
            </>
          ) : (
            "Select a node to trace its connections."
          )}
        </p>
      </figcaption>
    </figure>
  );
}
