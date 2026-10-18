"use client";

import { Background, BackgroundVariant, getViewportForBounds, ReactFlow, ReactFlowProvider, useReactFlow, useStore, type Edge } from "@xyflow/react";
import { AnimatePresence, motion as m } from "motion/react";
import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type RefObject } from "react";
import { useTheme } from "@/hooks/use-theme";
import { NodeGlyph, NODE_TYPE_NAMES } from "@/components/ask/NodeGlyph";
import { EDGE_VERBS } from "@/components/ask/EvidenceTrail";
import { CloseIcon, CollapseIcon, ExpandIcon, ExternalIcon, GitHubMark, LayersIcon, MinusIcon, PlusIcon, SearchIcon } from "@/components/WorkspaceIcons";
import type { EvidencePath } from "@/lib/types";
import { EvidenceGraphNode, NetworkFocus, type GraphNode } from "./EvidenceGraphNode";
import { layout } from "./graph-layout";

import { NetworkEdge } from "./NetworkEdge";

const edgeTypes = { network: NetworkEdge };
// Positions name the node's centre, so a node can grow at overview zoom and stay put.
const CENTRE: [number, number] = [0.5, 0.5];
const nodeTypes = { evidence: EvidenceGraphNode };
const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
// The camera glides between views; zoom buttons answer quickly.
const glide = (t: number) => (t < 0.5 ? 8 * t ** 4 : 1 - (-2 * t + 2) ** 4 / 2);
const settle = (t: number) => 1 - (1 - t) ** 3;
// Linear, not the default fly-to curve: that one pulls back mid-flight before closing in.
const camera = () => ({ duration: reduced() ? 0 : 700, ease: glide, interpolate: "linear" as const });
const nudge = () => ({ duration: reduced() ? 0 : 260, ease: settle, interpolate: "linear" as const });
// A line can stand for several relationship types (the graph model joins them): "authored · reviewed".
const verbOf = (type: string) => type.split("|").map(t => EDGE_VERBS[t] ?? t.toLowerCase().replaceAll("_", " ")).join(" · ");

type Props = {
  evidence: EvidencePath;
  stops: string[];
  highlighted: string | null;
  /** A source hovered in the answer; lit here without moving the camera. */
  hovered?: string | null;
  onHover?: (nodeId: string | null) => void;
  onSelect: (nodeId: string) => void;
  label: string;
  routeLabel?: string;
  /** The node the map is built around and opens on; defaults to the first stop. */
  anchor?: string;
  revision?: string;
  busy?: boolean;
  preview?: boolean;
  /** Nodes to light without selecting them or moving the camera, e.g. where a starter lands. */
  lit?: string[];
  /** Label every node at any zoom and draw it at full size, for small maps whose names are the point. */
  labelled?: boolean;
  /** Hand-placed positions, for a drawing designed rather than found by the forces. */
  positions?: Record<string, [number, number]>;
};

/** Writes the zoom to a CSS variable, so nodes can keep a 26px target at overview zoom without
 * handing React Flow new node objects on every camera frame. */
function ZoomVariable({ target }: { target: RefObject<HTMLDivElement | null> }) {
  const zoom = useStore(s => s.transform[2]);
  useEffect(() => { target.current?.style.setProperty("--zoom", String(zoom)); }, [zoom, target]);
  return null;
}

export function EvidenceMap(props: Props) {
  return <ReactFlowProvider><Network {...props} /></ReactFlowProvider>;
}

function Network({ evidence, stops, highlighted, hovered = null, onHover, onSelect, label, routeLabel = "route through the cited sources", anchor, revision, busy, preview = false, lit, labelled = false, positions }: Props) {
  const theme = useTheme();
  const container = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLDivElement>(null);
  const optionsRef = useRef<HTMLDivElement>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [fullscreenError, setFullscreenError] = useState("");
  const [search, setSearch] = useState("");
  const [edgeLabels, setEdgeLabels] = useState(false);
  const [options, setOptions] = useState(false);
  const flow = useReactFlow<GraphNode>();
  const width = useStore(s => s.width);
  const height = useStore(s => s.height);
  const stopKey = JSON.stringify(stops);
  const drawn = useMemo(() => layout(evidence, JSON.parse(stopKey), 0.85, 760, anchor, positions), [evidence, stopKey, anchor, positions]);
  // A crowded map opens on its route, centred on the anchor; a small one opens whole.
  const dense = evidence.nodes.length > 30;
  const neighbours = useMemo(() => {
    const ids = new Set<string>();
    for (const e of drawn.links) {
      if (e.source === highlighted) ids.add(e.target);
      if (e.target === highlighted) ids.add(e.source);
    }
    return ids;
  }, [drawn, highlighted]);
  // While an answer loads, the previous one is drawn plain: the route is coloured, and drawn,
  // only once the new answer lands.
  const plain = preview || Boolean(busy);
  // Node objects change only when that node does. React Flow re-measures every node it is handed
  // as a new object, and edges unmount until it has: rebuilding all of them on hover made the
  // whole map blink and the route draw itself again. Hover and dimming travel by context instead.
  const baseNodes: GraphNode[] = useMemo(() => drawn.nodes.map((n, order) => {
    const index = drawn.present.indexOf(n.id);
    return {
      id: n.id, type: "evidence", position: { x: n.x, y: n.y },
      data: { evidence: n, order, anchor: !plain && n.id === drawn.anchor, onRoute: !plain && drawn.onRoute.has(n.id), stop: plain || index < 0 ? undefined : index + 1, labelled },
      selected: false, draggable: false, ariaRole: "button",
      ariaLabel: `${index < 0 ? "" : `Source ${index + 1}, `}${NODE_TYPE_NAMES[n.label] ?? n.label}: ${n.title}`,
      domAttributes: { "aria-pressed": false },
    };
  }), [drawn, plain, labelled]);
  const nodes = useMemo(() => baseNodes.map(n => n.id === highlighted ? { ...n, selected: true, domAttributes: { "aria-pressed": true } } : n), [baseNodes, highlighted]);
  const litKey = lit?.length ? lit.join("|") : "";
  const litSet = useMemo(() => litKey ? new Set(litKey.split("|")) : null, [litKey]);
  const focusState = useMemo(() => ({ highlighted, hovered, neighbours, lit: litSet }), [highlighted, hovered, neighbours, litSet]);
  const edges: Edge[] = useMemo(() => {
    // Each leg remembers its place in citation order, so the route draws itself in that order.
    const route = new Map(drawn.legs.flatMap((leg, order) => leg.slice(1).flatMap((n, i) => [[`${leg[i].id}|${n.id}`, order], [`${n.id}|${leg[i].id}`, order]] as const)));
    return drawn.links.map((e, i) => {
      const leg = route.get(`${e.source}|${e.target}`);
      const cited = !plain && leg !== undefined;
      const related = e.source === highlighted || e.target === highlighted;
      const glowing = litSet !== null && litSet.has(e.source) && litSet.has(e.target);
      const faded = (highlighted !== null && !related) || (litSet !== null && !glowing);
      return { ...e, id: `${e.source}-${e.type}-${e.target}-${i}`, type: "network", selectable: false,
        className: [cited && "route-leg", related && "is-related", glowing && "is-lit", faded && "is-faded"].filter(Boolean).join(" ") || undefined,
        data: { delay: cited ? 120 + Math.min(leg ?? 0, 16) * 70 : undefined, sourceRadius: labelled ? 17 : !plain && e.source === drawn.anchor ? 19 : !plain && drawn.present.includes(e.source) ? 17 : !plain && drawn.onRoute.has(e.source) ? 10 : 6, targetRadius: labelled ? 19 : !plain && e.target === drawn.anchor ? 21 : !plain && drawn.present.includes(e.target) ? 19 : !plain && drawn.onRoute.has(e.target) ? 12 : 8 },
        label: edgeLabels || related ? verbOf(e.type) : undefined,
        labelStyle: { fontSize: 10.5, fontWeight: 500, fill: "var(--muted)" }, labelBgStyle: { fill: "var(--surface)", stroke: "var(--rule)", strokeWidth: 1 }, labelBgPadding: [6, 3],
        style: { stroke: related || glowing ? "var(--ink)" : cited ? "var(--path)" : "var(--graph-edge)", strokeWidth: cited ? 1.8 : related || glowing ? 1.5 : 1 },
      };
    });
  }, [drawn, highlighted, edgeLabels, plain, litSet, labelled]);

  const cameraIntent = useRef<"all" | "sources" | "selected">(highlighted ? "selected" : dense && !preview ? "sources" : "all");
  const lastSelection = useRef(highlighted);
  const lastRevision = useRef(revision);
  // Explicit bounds keep camera commands deterministic when selection and resize coincide.
  // Include labels in the bounds; the library measures only the circular node itself.
  const focus = useCallback((ids?: Set<string>, maxZoom = 1.05) => {
    const targets = ids ? drawn.nodes.filter(n => ids.has(n.id)) : drawn.nodes;
    if (!targets.length || !width || !height) return;
    const left = Math.min(...targets.map(n => n.x)) - 85;
    const top = Math.min(...targets.map(n => n.y)) - 70;
    const right = Math.max(...targets.map(n => n.x)) + 85;
    const bottom = Math.max(...targets.map(n => n.y)) + 90;
    const viewport = getViewportForBounds({ x: left, y: top, width: right - left, height: bottom - top }, width, height, 0.15, maxZoom, 0.1);
    void flow.setViewport(viewport, camera());
  }, [drawn, width, height, flow]);
  // The route, framed symmetrically around the anchor so the anchor lands in the middle.
  const focusRoute = useCallback(() => {
    const centre = drawn.placed.get(drawn.anchor ?? "");
    const targets = drawn.nodes.filter(n => drawn.onRoute.has(n.id));
    if (!centre || !targets.length || !width || !height) { focus(drawn.onRoute, 1.25); return; }
    const halfX = Math.max(...targets.map(n => Math.abs(n.x - centre.x))) + 85;
    const halfY = Math.max(...targets.map(n => Math.abs(n.y - centre.y))) + 90;
    // Never so far out that nodes (kept about 128 apart) crowd below a 26px target.
    const fit = getViewportForBounds({ x: centre.x - halfX, y: centre.y - halfY, width: halfX * 2, height: halfY * 2 }, width, height, 0.22, 1.25, 0.1);
    const at = (zoom: number) => ({ x: width / 2 - centre.x * zoom, y: height / 2 - centre.y * zoom, zoom });
    const cut = (zoom: number) => {
      const r = Math.max(22, 13 / zoom), w = width / zoom / 2, h = height / zoom / 2;
      return drawn.nodes.some(n => {
        const dx = Math.abs(n.x - centre.x), dy = Math.abs(n.y - centre.y);
        return dx - r < w && dy - r < h && (dx + r > w || dy + r > h);
      });
    };
    // Step out from the route's own framing to the nearest zoom where no node is cut by the edge:
    // a half-visible node is a target too small to hit. Usually a step or two is enough.
    let zoom = fit.zoom;
    for (let step = 1; cut(zoom) && step <= 30; step++) zoom = Math.max(fit.zoom * (1 - step * 0.03), 0.22);
    const viewport = cut(zoom) ? fit : at(zoom);
    void flow.setViewport(viewport, camera());
  }, [drawn, width, height, flow, focus]);
  useEffect(() => {
    if (revision !== lastRevision.current) cameraIntent.current = dense && !preview ? "sources" : "all";
    // Closing a node returns to the map's home view: the route when crowded, else everything.
    else if (highlighted !== lastSelection.current) cameraIntent.current = highlighted ? "selected" : dense && !preview ? "sources" : "all";
    lastRevision.current = revision;
    lastSelection.current = highlighted;
    // While an answer loads the camera holds still; it moves once, from here, when the answer lands.
    if (busy) return;
    if (cameraIntent.current === "selected" && highlighted) focus(new Set([highlighted, ...neighbours]), 1.35);
    else if (cameraIntent.current === "sources") focusRoute();
    else focus();
  }, [revision, busy, highlighted, neighbours, drawn, focus, focusRoute, flow, dense, preview]);
  useEffect(() => {
    const update = () => setFullscreen(document.fullscreenElement === container.current);
    document.addEventListener("fullscreenchange", update);
    return () => document.removeEventListener("fullscreenchange", update);
  }, []);
  // The options card closes like any popover: a click elsewhere or Escape.
  useEffect(() => {
    if (!options) return;
    const away = (event: PointerEvent) => { if (!optionsRef.current?.contains(event.target as Node)) setOptions(false); };
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") setOptions(false); };
    document.addEventListener("pointerdown", away);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("pointerdown", away); document.removeEventListener("keydown", escape); };
  }, [options]);
  const expand = async () => {
    try {
      if (document.fullscreenElement === container.current) await document.exitFullscreen();
      else await container.current?.requestFullscreen();
      setFullscreenError("");
    } catch { setFullscreenError("Your browser blocked fullscreen. You can still pan and zoom the map here."); }
  };
  const selected = evidence.nodes.find(n => n.id === highlighted);
  const titles = useMemo(() => new Map(evidence.nodes.map(n => [n.id, n])), [evidence]);
  const connections = useMemo(() => drawn.links.flatMap(e => {
    if (e.source === highlighted) return [{ id: e.target, verb: verbOf(e.type), outgoing: true }];
    if (e.target === highlighted) return [{ id: e.source, verb: verbOf(e.type), outgoing: false }];
    return [];
  }).filter(c => titles.has(c.id)), [drawn, highlighted, titles]);
  const matches = search.trim() ? evidence.nodes.filter(n => `${n.title} ${n.label} ${n.id}`.toLowerCase().includes(search.trim().toLowerCase())) : [];
  const types = [...new Set(evidence.nodes.map(n => n.label))];

  if (!evidence.nodes.length) return <p className="p-6 text-sm text-muted">Nothing to map. This answer didn&apos;t use the graph.</p>;
  return (
    <div ref={container} className="network-shell" data-preview={preview || undefined} data-dense={evidence.nodes.length > 30 || undefined} data-fullscreen={fullscreen || undefined} data-busy={busy || undefined} data-labelled={labelled || undefined}>
      <div className="network-stage">
      <div ref={canvas} className="network-canvas" onKeyDownCapture={(event) => { const id = (event.target as HTMLElement).closest(".react-flow__node")?.getAttribute("data-id"); if (id && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); event.stopPropagation(); onSelect(id); } }} role="group" aria-label={`${label}: ${nodes.length} nodes and ${edges.length} connections. The Path tab lists the same nodes as text.`}>
        <NetworkFocus.Provider value={focusState}>
        <ReactFlow<GraphNode> nodes={nodes} edges={edges} nodeTypes={nodeTypes} edgeTypes={edgeTypes} colorMode={theme} nodeOrigin={CENTRE}
          minZoom={0.15} maxZoom={2.5}
          nodesDraggable={false} nodesConnectable={false} edgesFocusable={false} deleteKeyCode={null}
          onNodeClick={(_, node) => onSelect(node.id)} onNodeMouseEnter={(_, node) => onHover?.(node.id)} onNodeMouseLeave={() => onHover?.(null)} onPaneClick={() => { if (highlighted) onSelect(highlighted); }}
          autoPanOnNodeFocus preventScrolling={false} zoomOnDoubleClick={false}>
          <Background variant={BackgroundVariant.Dots} gap={24} size={1.2} color="var(--graph-grid)" />
          <ZoomVariable target={canvas} />
        </ReactFlow>
        </NetworkFocus.Provider>
        {busy && <span className="network-progress" aria-hidden="true" />}
      </div>
      <AnimatePresence>
        {selected && <m.section key="inspector" className="network-inspector" aria-label="Selected node" aria-live="polite"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, transition: { duration: 0.14 } }} transition={{ duration: 0.2 }}>
          {/* Moving between nodes swaps only the contents, so the panel itself stays put. */}
          <m.div key={selected.id} className="inspector-body" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28, ease: [0.2, 0.7, 0.2, 1] }}>
            {/* The type is carried by the glyph tile and a quiet meta line, not a label of its own. */}
            <div className="inspector-head" style={{ "--node-color": `var(--node-${selected.label.toLowerCase()}, var(--muted))` } as CSSProperties}>
              <span className="inspector-glyph" aria-hidden="true"><NodeGlyph label={selected.label} /></span>
              <div className="inspector-heading">
                <strong className="inspector-title">{selected.title}</strong>
                <p className="inspector-meta">{NODE_TYPE_NAMES[selected.label] ?? selected.label} · {neighbours.size ? `${neighbours.size} connected ${neighbours.size === 1 ? "node" : "nodes"}` : "No connections returned for this node"}</p>
              </div>
              <button type="button" className="inspector-close" aria-label="Close node details" onClick={() => onSelect(selected.id)}><CloseIcon /></button>
            </div>
            {selected.url && <a className="inspector-link" href={selected.url} target="_blank" rel="noreferrer"><GitHubMark size={13} />Open on GitHub<ExternalIcon /></a>}
            {connections.length > 0 && <div className="inspector-connections">
              <h3>Connected</h3>
              <ul>
                {connections.map((c, i) => {
                  const node = titles.get(c.id)!;
                  return <li key={`${c.id}-${i}`}>
                    <button type="button" aria-label={`${node.title}, ${c.outgoing ? c.verb : `${c.verb} this`}`} onClick={() => onSelect(c.id)}
                      onMouseEnter={() => onHover?.(c.id)} onMouseLeave={() => onHover?.(null)} onFocus={() => onHover?.(c.id)} onBlur={() => onHover?.(null)}>
                      <NodeGlyph label={node.label} />
                      <span className="inspector-connection-text">
                        <span className="inspector-connection-verb">{c.outgoing ? c.verb : `${c.verb} this`}</span>
                        <span className="inspector-connection-title">{node.title}</span>
                      </span>
                    </button>
                  </li>;
                })}
              </ul>
            </div>}
          </m.div>
        </m.section>}
      </AnimatePresence>
      </div>
      <div className="network-tools">
        <div className="network-search">
          <SearchIcon />
          <input type="search" aria-label="Find a node" placeholder="Find a person, PR, file…" value={search} onChange={e => setSearch(e.target.value)} onKeyDown={e => { if (e.key === "Escape") setSearch(""); }} />
          <AnimatePresence>
            {search.trim() && <m.div className="network-search-results" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 4, transition: { duration: 0.12 } }} transition={{ duration: 0.2, ease: [0.2, 0.7, 0.2, 1] }}>
              {matches.length === 0 ? <p>No matching nodes in this answer.</p> : matches.map(n => <button type="button" key={n.id} aria-label={`Find ${NODE_TYPE_NAMES[n.label] ?? n.label}: ${n.title}`} onClick={() => { onSelect(n.id); setSearch(""); }}><NodeGlyph label={n.label} /><span>{n.title}</span></button>)}
            </m.div>}
          </AnimatePresence>
        </div>
        <div className="network-navigation" aria-label="Graph navigation">
          <button type="button" title="Zoom in" aria-label="Zoom in" onClick={() => void flow.zoomIn(nudge())}><PlusIcon /></button>
          <button type="button" title="Zoom out" aria-label="Zoom out" onClick={() => void flow.zoomOut(nudge())}><MinusIcon /></button>
          <span className="network-navigation-rule" aria-hidden="true" />
          <button type="button" aria-label="Fit all nodes" onClick={() => { cameraIntent.current = "all"; focus(); }}>Fit all</button>
          {!preview && <button type="button" aria-label="Focus cited sources" disabled={!drawn.onRoute.size} onClick={() => { cameraIntent.current = "sources"; focusRoute(); }}>Focus sources</button>}
        </div>
        <button type="button" className="network-control" onClick={() => void expand()} aria-label={fullscreen ? "Exit fullscreen graph" : "Fullscreen graph"} title={fullscreen ? "Exit fullscreen" : "Fullscreen"}>{fullscreen ? <CollapseIcon /> : <ExpandIcon />}</button>
        <div className="network-options-anchor" ref={optionsRef}>
          <button type="button" className="network-control" aria-label="Graph options" title="Legend and labels" aria-expanded={options} aria-controls="graph-options" data-open={options || undefined} onClick={() => setOptions(v => !v)}><LayersIcon /></button>
          <AnimatePresence>
            {options && <m.div className="network-options" id="graph-options" initial={{ opacity: 0, y: 6, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 4, scale: 0.98, transition: { duration: 0.12 } }} transition={{ duration: 0.22, ease: [0.2, 0.7, 0.2, 1] }}>
              <p className="network-count">{nodes.length} nodes · {edges.length} connections</p>
              <div className="network-legend">
                {types.map(t => <span key={t}><NodeGlyph label={t} /><span>{NODE_TYPE_NAMES[t] ?? t}</span></span>)}
              </div>
              <label className="network-switch"><span>Edge labels</span><input type="checkbox" checked={edgeLabels} onChange={e => setEdgeLabels(e.target.checked)} /></label>
              <div className="network-help"><span>{drawn.legs.length ? routeLabel : "All evidence returned for this answer"}</span><span>All nodes shown · zoom for labels</span></div>
            </m.div>}
          </AnimatePresence>
        </div>
      </div>
      {fullscreenError && <p role="status" className="px-3 pb-3 text-sm text-danger">{fullscreenError}</p>}
    </div>
  );
}
