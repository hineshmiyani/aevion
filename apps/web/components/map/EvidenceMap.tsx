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
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";

import { NODE_SHAPES, NODE_TYPE_NAMES } from "@/components/ask/NodeGlyph";
import type { EvidenceNode, EvidencePath } from "@/lib/types";

/*
 * The evidence map (AEV-43). The answer's sources are stops on a route; the route follows the
 * graph's own edges between consecutive stops ([1] → [2] → [3]) and draws itself once, leg by
 * leg, when an answer arrives. Only the clusters the answer cites are drawn.
 */

const W = 760;
const GLYPH = 16;
const LEG_STAGGER_MS = 320;

type Placed = EvidenceNode & SimulationNodeDatum & { x: number; y: number };
type Link = { source: string; target: string; type: string };

/** A short map label: what a reader would call the node, not its full title. */
export function shortLabel(node: EvidenceNode, max = 28): string {
  const key = node.id.split(":").slice(1).join(":");
  const trim = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);
  switch (node.label) {
    case "PullRequest":
    case "Issue":
      return `#${key.split("#").pop()}`;
    case "File":
      return key.split("/").pop() ?? node.title;
    case "Component":
      return node.title === "(root)" ? "repo root" : trim(node.title, max - 2);
    case "Comment":
      return "";
    default:
      return trim(node.title, max);
  }
}

const EMPTY = {
  nodes: [] as Placed[],
  links: [] as Link[],
  viewBox: "0 0 1 1",
  vbWidth: 1,
  vbHeight: 1,
  max: 28,
  legs: [] as Placed[][],
  onRoute: new Set<string>(),
  present: [] as string[],
  placed: new Map<string, Placed>(),
};

const ALWAYS_LABELLED = new Set(["Person", "Component", "Decision", "PullRequest", "Issue", "Release"]);

function components(nodes: string[], links: Link[]): Map<string, number> {
  const adj = new Map<string, string[]>(nodes.map((n) => [n, []]));
  for (const l of links) {
    adj.get(l.source)?.push(l.target);
    adj.get(l.target)?.push(l.source);
  }
  const group = new Map<string, number>();
  let g = 0;
  for (const start of nodes) {
    if (group.has(start)) continue;
    const queue = [start];
    group.set(start, g);
    while (queue.length) {
      const id = queue.shift()!;
      for (const next of adj.get(id) ?? []) {
        if (group.has(next)) continue;
        group.set(next, g);
        queue.push(next);
      }
    }
    g += 1;
  }
  return group;
}

/** Shortest path between two nodes over the (undirected) evidence edges. */
function shortestPath(from: string, to: string, links: Link[]): string[] | null {
  const adj = new Map<string, string[]>();
  for (const l of links) {
    adj.set(l.source, [...(adj.get(l.source) ?? []), l.target]);
    adj.set(l.target, [...(adj.get(l.target) ?? []), l.source]);
  }
  const prev = new Map<string, string | null>([[from, null]]);
  const queue = [from];
  while (queue.length) {
    const id = queue.shift()!;
    if (id === to) break;
    for (const next of adj.get(id) ?? []) {
      if (prev.has(next)) continue;
      prev.set(next, id);
      queue.push(next);
    }
  }
  if (!prev.has(to)) return null;
  const path: string[] = [];
  for (let at: string | null = to; at !== null; at = prev.get(at) ?? null) path.unshift(at);
  return path;
}

function layout(evidence: EvidencePath, stops: string[], aspect: number, boxWidth: number) {
  // Narrow boxes (phones) get shorter labels; label width is budgeted at the zoom in use.
  const max = boxWidth < 520 ? 14 : 28;
  const label = (n: EvidenceNode) => shortLabel(n, max);
  const charWidth = 6.6 * Math.min(Math.max(W / boxWidth, 0.7), 2.2);
  // Lay out for the box the map is drawn in, so a tall panel gets a tall map.
  const H = Math.round(W * Math.min(Math.max(aspect, 0.5), 1.6));
  const known = new Set(evidence.nodes.map((n) => n.id));
  let links: Link[] = evidence.edges.filter((e) => known.has(e.source) && known.has(e.target));
  const group = components([...known], links);
  // Keep the clusters the route visits; without stops, the largest cluster.
  const stopGroups = new Set(stops.filter((s) => known.has(s)).map((s) => group.get(s)));
  if (stopGroups.size === 0) {
    const sizes = new Map<number, number>();
    group.forEach((g) => sizes.set(g, (sizes.get(g) ?? 0) + 1));
    const largest = [...sizes.entries()].sort((a, b) => b[1] - a[1])[0]?.[0];
    if (largest !== undefined) stopGroups.add(largest);
  }
  let kept = evidence.nodes.filter((n) => stopGroups.has(group.get(n.id)));
  let keptIds = new Set(kept.map((n) => n.id));
  links = links.filter((l) => keptIds.has(l.source) && keptIds.has(l.target));

  // The route, from the graph's shape alone: consecutive stops joined by shortest paths.
  const present = stops.filter((s) => keptIds.has(s));
  const legIds: string[][] = [];
  for (let i = 1; i < present.length; i++) {
    const path = shortestPath(present[i - 1], present[i], links);
    if (path && path.length > 1) legIds.push(path);
  }
  // A phone can't show 50 nodes legibly: draw the route itself; the Path tab lists the rest.
  if (boxWidth < 520 && legIds.length > 0) {
    keptIds = new Set([...legIds.flat(), ...present]);
    kept = kept.filter((n) => keptIds.has(n.id));
    links = links.filter((l) => keptIds.has(l.source) && keptIds.has(l.target));
  }

  const nodes = kept.map((n) => ({ ...n })) as Placed[];
  const simulation = forceSimulation(nodes)
    .force("link", forceLink<Placed, { source: string | Placed; target: string | Placed }>(links.map((l) => ({ ...l }))).id((d) => d.id).distance(70))
    .force("charge", forceManyBody().strength(-420))
    // Room for each label at the zoom it will be drawn at (wider on phones).
    .force("collide", forceCollide<Placed>((d) => (label(d) ? Math.min(14 + label(d).length * charWidth * 0.42, 96) : 16)))
    .force("center", forceCenter(W / 2, H / 2))
    // Pull harder along the box's short side, so the drawing fills its shape.
    .force("x", forceX(W / 2).strength(H > W ? 0.09 : 0.03))
    .force("y", forceY(H / 2).strength(H > W ? 0.03 : 0.09))
    .stop();
  simulation.tick(320);

  const pad = 56;
  const minX = Math.min(...nodes.map((n) => n.x)) - pad;
  const minY = Math.min(...nodes.map((n) => n.y)) - pad;
  const maxX = Math.max(...nodes.map((n) => n.x + (label(n) ? 16 + label(n).length * charWidth : 0))) + pad / 2;
  const maxY = Math.max(...nodes.map((n) => n.y)) + pad;
  const vbWidth = Math.max(maxX - minX, 320);
  const vbHeight = Math.max(maxY - minY, 240);
  const viewBox = `${minX} ${minY} ${vbWidth} ${vbHeight}`;

  const placed = new Map(nodes.map((n) => [n.id, n]));
  const legs = legIds.map((path) => path.map((id) => placed.get(id)!));
  const onRoute = new Set(legs.flat().map((n) => n.id).concat(present));
  return { nodes, links, viewBox, vbWidth, vbHeight, legs, onRoute, present, placed, max };
}

type EvidenceMapProps = {
  evidence: EvidencePath;
  /** Node ids in reading order (the answer's citations); the route visits them in turn. */
  stops: string[];
  highlighted: string | null;
  onSelect: (nodeId: string) => void;
  label: string;
  /** What the route means here, for the legend. */
  routeLabel?: string;
};

export function EvidenceMap({ evidence, stops, highlighted, onSelect, label, routeLabel = "route through the cited sources" }: EvidenceMapProps) {
  const box = useRef<HTMLDivElement>(null);
  const [aspect, setAspect] = useState<number | null>(null); // unknown until measured
  const [boxWidth, setBoxWidth] = useState(620);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const measure = () => {
      const { width, height } = el.getBoundingClientRect();
      // Re-lay out only when the shape really changes, not on every pixel of a resize.
      if (width > 0 && height > 0) {
        setBoxWidth((prev) => (Math.abs(prev - width) > 60 ? width : prev));
        setAspect((prev) => (prev !== null && Math.abs(prev - height / width) <= 0.12 ? prev : height / width));
      }
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  const drawn = useMemo(() => (aspect === null ? null : layout(evidence, stops, aspect, boxWidth)), [evidence, stops, aspect, boxWidth]);
  const { nodes, links, viewBox, vbWidth, vbHeight, legs, onRoute, present, placed, max } = drawn ?? EMPTY;
  // SVG units per screen pixel: glyphs, labels and strokes keep their on-screen size at any zoom.
  // "meet" fits the tighter axis, so a tall layout in a wide box is scaled by its height.
  const boxHeight = boxWidth * (aspect ?? 1);
  const k = Math.min(Math.max(vbWidth / boxWidth, vbHeight / boxHeight, 0.7), 2.2);
  const G = GLYPH * k;
  const stopNumber = new Map(present.map((id, i) => [id, i + 1]));
  const selected = highlighted ? placed.get(highlighted) : undefined;
  const neighbours = useMemo(() => {
    const set = new Set<string>();
    for (const l of links) {
      if (l.source === highlighted) set.add(l.target);
      if (l.target === highlighted) set.add(l.source);
    }
    return set;
  }, [links, highlighted]);
  const types = [...new Set(nodes.map((n) => n.label))];

  const onKey = (event: KeyboardEvent, id: string) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(id);
    }
  };

  if (evidence.nodes.length === 0) {
    return <p className="p-6 text-sm text-muted">Nothing to map. This answer didn&apos;t use the graph.</p>;
  }

  return (
    <figure className="m-0 flex h-full flex-col">
      <div ref={box} className="survey-grid relative min-h-0 flex-1 overflow-hidden border border-rule">
        <svg
          viewBox={viewBox}
          preserveAspectRatio="xMidYMid meet"
          role="group"
          aria-label={`${label}: ${nodes.length} nodes and ${links.length} connections${legs.length ? `, with a route through ${present.length} cited sources` : ""}. The Path tab lists the same nodes as text.`}
          className="absolute inset-0 h-full w-full"
        >
          <g aria-hidden>
            {links.map((l, i) => {
              const a = placed.get(l.source)!;
              const b = placed.get(l.target)!;
              const lit = highlighted !== null && (l.source === highlighted || l.target === highlighted);
              return (
                <line
                  key={i}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke={lit ? "var(--ink)" : "var(--rule)"}
                  strokeWidth={(lit ? 1.5 : 1) * k}
                />
              );
            })}
            {legs.map((leg, i) => {
              const length = leg.slice(1).reduce((sum, n, j) => sum + Math.hypot(n.x - leg[j].x, n.y - leg[j].y), 0);
              return (
                <polyline
                  key={`leg-${i}`}
                  className="route-leg"
                  points={leg.map((n) => `${n.x},${n.y}`).join(" ")}
                  fill="none"
                  stroke="var(--path)"
                  strokeWidth={3.5 * k}
                  strokeLinecap="square"
                  strokeLinejoin="miter"
                  style={{ ["--len" as string]: `${Math.ceil(length) + 2}`, animationDelay: `${i * LEG_STAGGER_MS}ms` }}
                />
              );
            })}
          </g>
          {nodes.map((n) => {
            const isSelected = n.id === highlighted;
            const dimmed = highlighted !== null && !isSelected && !neighbours.has(n.id) && !onRoute.has(n.id);
            const text = shortLabel(n, max);
            const showLabel = text && (ALWAYS_LABELLED.has(n.label) || onRoute.has(n.id) || isSelected);
            const stop = stopNumber.get(n.id);
            const name = NODE_TYPE_NAMES[n.label] ?? n.label;
            const focusable = Boolean(showLabel || stop);
            return (
              <g
                key={n.id}
                role="button"
                tabIndex={focusable ? 0 : -1}
                aria-pressed={isSelected}
                aria-label={`${stop ? `Source ${stop}, ` : ""}${name}: ${n.title}`}
                onClick={() => onSelect(n.id)}
                onKeyDown={(e) => onKey(e, n.id)}
                transform={`translate(${n.x} ${n.y})`}
                opacity={dimmed ? 0.3 : 1}
                className="cursor-pointer outline-none transition-opacity duration-200 [&:focus-visible>rect.focus]:opacity-100"
              >
                <rect className="focus opacity-0" x={-G} y={-G} width={G * 2} height={G * 2} fill="none" stroke="var(--path)" strokeWidth={2 * k} />
                {(isSelected || stop) && (
                  <rect x={-G * 0.85} y={-G * 0.85} width={G * 1.7} height={G * 1.7} fill={isSelected ? "var(--path-soft)" : "var(--surface)"} stroke="var(--path)" strokeWidth={(stop ? 2 : 1.5) * k} />
                )}
                <g
                  transform={`translate(${-G / 2} ${-G / 2}) scale(${G / 14})`}
                  style={{ color: `var(--node-${n.label.toLowerCase()}, var(--muted))` }}
                  fill={n.label === "Release" ? "none" : "currentColor"}
                  stroke="currentColor"
                  strokeWidth={n.label === "Release" ? 1.6 : 0}
                >
                  {NODE_SHAPES[n.label] ?? <circle cx="7" cy="7" r="4" />}
                </g>
                {stop && (
                  <g transform={`translate(${G * 0.55} ${-G * 0.95})`} aria-hidden>
                    <rect x={-7.5 * k} y={-7.5 * k} width={15 * k} height={15 * k} fill="var(--path)" />
                    <text textAnchor="middle" y={3.4 * k} fontSize={9.5 * k} fontWeight={600} fill="var(--surface)" className="font-sans tabular-nums">
                      {stop}
                    </text>
                  </g>
                )}
                {showLabel && (
                  <text
                    x={G * 0.85}
                    y={4 * k}
                    fontSize={12.5 * k}
                    fontWeight={onRoute.has(n.id) ? 600 : 400}
                    className="fill-ink font-sans"
                    paintOrder="stroke"
                    stroke="var(--surface)"
                    strokeWidth={4 * k}
                    strokeLinejoin="round"
                  >
                    {text}
                  </text>
                )}
                <title>{`${name}: ${n.title}`}</title>
              </g>
            );
          })}
        </svg>

        {selected && (
          <div className="arrive absolute right-3 bottom-3 left-3 max-w-md border border-rule bg-surface/95 p-3 text-sm shadow-[0_6px_20px_-8px_rgb(0_0_0/0.25)] sm:right-auto" aria-live="polite">
            <p className="text-xs text-muted">{NODE_TYPE_NAMES[selected.label] ?? selected.label}</p>
            <p className="mt-0.5 leading-snug text-ink">{selected.title}</p>
            {selected.url && (
              <a href={selected.url} target="_blank" rel="noreferrer" className="mt-1.5 inline-block text-path underline underline-offset-2">
                Open on GitHub
              </a>
            )}
          </div>
        )}
      </div>

      <figcaption className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
        {legs.length > 0 && (
          <span className="flex items-center gap-1.5">
            <svg width="18" height="6" aria-hidden>
              <line x1="1" y1="3" x2="17" y2="3" stroke="var(--path)" strokeWidth="3" />
            </svg>
            {routeLabel}
          </span>
        )}
        {types.map((t) => (
          <span key={t} className="flex items-center gap-1.5">
            <svg viewBox="0 0 14 14" width="11" height="11" aria-hidden style={{ color: `var(--node-${t.toLowerCase()}, var(--muted))` }} fill={t === "Release" ? "none" : "currentColor"} stroke="currentColor" strokeWidth={t === "Release" ? 1.6 : 0}>
              {NODE_SHAPES[t]}
            </svg>
            {NODE_TYPE_NAMES[t] ?? t}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}
