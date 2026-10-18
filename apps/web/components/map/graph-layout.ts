import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY, type SimulationNodeDatum } from "d3-force";
import type { EvidenceNode, EvidencePath } from "@/lib/types";

const W = 760;
type Placed = EvidenceNode & SimulationNodeDatum & { x: number; y: number };
type Link = { source: string; target: string; type: string };

/** A short map label: what a reader would call the node, not its full title. */
export function shortLabel(node: EvidenceNode, max = 28): string {
  // Graph-model nodes (lib/graph-schema.ts) are named for what they stand for.
  if (node.id.startsWith("Schema:")) return node.title;
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

/** `anchor` is the node the drawing is built around: pinned at the centre, with the route
 * pulled in close to it. It defaults to the first stop. `positions` pins nodes where a drawing
 * is designed by hand (the graph model) instead of found by the forces. */
export function layout(evidence: EvidencePath, stops: string[], aspect: number, boxWidth: number, anchor?: string, positions?: Record<string, [number, number]>) {
  // Narrow boxes (phones) get shorter labels; label width is budgeted at the zoom in use.
  void boxWidth;
  const max = 24;
  const label = (n: EvidenceNode) => shortLabel(n, max);
  const charWidth = 5;
  // Lay out for the box the map is drawn in, so a tall panel gets a tall map.
  const H = Math.round(W * Math.min(Math.max(aspect, 0.5), 1.6));
  const known = new Set(evidence.nodes.map((n) => n.id));
  const links: Link[] = evidence.edges.filter((e) => known.has(e.source) && known.has(e.target));
  const group = components([...known], links);
  const kept = evidence.nodes;
  const keptIds = new Set(known);

  // The route, from the graph's shape alone: consecutive stops joined by shortest paths.
  const present = stops.filter((s) => keptIds.has(s));
  const legIds: string[][] = [];
  for (let i = 1; i < present.length; i++) {
    const path = shortestPath(present[i - 1], present[i], links);
    if (path && path.length > 1) legIds.push(path);
  }
  // Clusters the route doesn't run through, and loose nodes, have nothing tying them to the
  // rest, so charge alone pushes them to the edges. They get a stronger pull to the middle.
  const degree = new Map<string, number>();
  for (const l of links) for (const id of [l.source, l.target]) degree.set(id, (degree.get(id) ?? 0) + 1);
  const mainGroup = group.get(present[0] ?? kept[0]?.id ?? "");
  const loose = (d: Placed) => group.get(d.id) !== mainGroup;
  const pullX = H > W ? 0.35 : 0.03;
  const pullY = H > W ? 0.01 : 0.09;
  const onRouteIds = new Set(legIds.flat().concat(present));
  const idOf = (end: string | Placed) => (typeof end === "string" ? end : end.id);
  const centre = keptIds.has(anchor ?? "") ? anchor! : present[0];

  // Nodes with no edges at all can't be placed by the forces; they are set out in rows later.
  const nodes = kept.filter((n) => degree.get(n.id)).map((n) => ({ ...n })) as Placed[];
  const lone = kept.filter((n) => !degree.get(n.id)).map((n) => ({ ...n, x: 0, y: 0 })) as Placed[];
  for (const n of nodes) {
    const pin = positions?.[n.id];
    if (pin) { n.x = n.fx = pin[0]; n.y = n.fy = pin[1]; }
    else if (n.id === centre && !positions) { n.fx = W / 2; n.fy = H / 2; }
  }
  // When the anchor sits mid-route, the legs before it lead in from the left and the legs after
  // it lead out to the right, so the route reads across the anchor instead of bunching on one side.
  const at = present.indexOf(centre ?? "");
  const side = new Map<string, number>();
  if (at > 0 && at < present.length - 1) {
    legIds.forEach((leg, i) => leg.forEach((id) => { if (id !== centre && !side.has(id)) side.set(id, i < at ? -1 : 1); }));
  }
  const simulation = forceSimulation(nodes)
    .force("link", forceLink<Placed, { source: string | Placed; target: string | Placed }>(links.map((l) => ({ ...l }))).id((d) => d.id)
      // Route legs are held taut, so the answer reads as one compact shape. Their length stays at
      // 120: shorter, and neighbouring nodes overlap as tap targets at phone zoom.
      .distance(120)
      .strength((l) => (onRouteIds.has(idOf(l.source)) && onRouteIds.has(idOf(l.target)) ? 0.9 : 0.5)))
    .force("charge", forceManyBody().strength(-650))
    // Keep enough separation for touch targets while glyphs stay compact.
    .force("collide", forceCollide<Placed>(64).iterations(4))
    // Pull harder along the box's short side, so the drawing fills its shape; the route is held
    // close to the anchor, and separate clusters only gently, so they settle around it.
    .force("x", forceX<Placed>((d) => W / 2 + (side.get(d.id) ?? 0) * 170).strength((d) => (onRouteIds.has(d.id) ? 0.18 : loose(d) ? 0.08 : pullX)))
    .force("y", forceY<Placed>(H / 2).strength((d) => (onRouteIds.has(d.id) ? 0.18 : loose(d) ? 0.08 : pullY)))
    .stop();
  // Without a pinned anchor, centring keeps the drawing in the box instead.
  if (!centre) simulation.force("center", forceCenter(W / 2, H / 2));
  simulation.tick(320);

  // Unconnected evidence sits in tidy rows under the drawing, grouped by type.
  if (lone.length) {
    // The same spacing the forces keep, so these stay separate tap targets at overview zoom.
    const gap = 128;
    const left = nodes.length ? Math.min(...nodes.map((n) => n.x)) : W / 2;
    const right = nodes.length ? Math.max(...nodes.map((n) => n.x)) : W / 2;
    const perRow = Math.max(Math.floor((right - left) / gap) + 1, 4);
    const top = (nodes.length ? Math.max(...nodes.map((n) => n.y)) : H / 2) + gap;
    lone.sort((a, b) => a.label.localeCompare(b.label));
    lone.forEach((n, i) => {
      const row = Math.floor(i / perRow);
      const inRow = Math.min(perRow, lone.length - row * perRow);
      n.x = (left + right) / 2 + (i % perRow - (inRow - 1) / 2) * gap;
      n.y = top + row * gap;
    });
    nodes.push(...lone);
  }

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
  return { nodes, links, viewBox, vbWidth, vbHeight, legs, onRoute, present, placed, max, anchor: centre };
}
