"use client";

import { Handle, Position, NodeToolbar, useStore, type Node, type NodeProps } from "@xyflow/react";
import { createContext, useContext, useEffect, useRef, useState, type CSSProperties } from "react";
import { NodeGlyph, NODE_TYPE_NAMES } from "@/components/ask/NodeGlyph";
import type { EvidenceNode } from "@/lib/types";
import { shortLabel } from "./graph-layout";

export type GraphNode = Node<{ evidence: EvidenceNode; stop?: number; onRoute: boolean; order?: number; anchor?: boolean; labelled?: boolean }, "evidence">;

/** What the reader is pointing at. Kept out of node data so hovering never hands React Flow new nodes. */
export const NetworkFocus = createContext<{ highlighted: string | null; hovered: string | null; neighbours: Set<string>; lit: Set<string> | null }>({ highlighted: null, hovered: null, neighbours: new Set(), lit: null });

export function EvidenceGraphNode({ id, data, selected }: NodeProps<GraphNode>) {
  const focus = useContext(NetworkFocus);
  // The route stays at full strength: it is the answer, and its numbers must stay readable.
  const lit = focus.lit?.has(id) ?? false;
  const dimmed = (focus.highlighted !== null && focus.highlighted !== id && !focus.neighbours.has(id) && !data.onRoute) || (focus.lit !== null && !lit);
  const linked = focus.hovered === id || lit;
  const [hovered, setHovered] = useState(false);
  // The tooltip waits for a moment of intent, so sweeping across the map doesn't flash cards.
  const [tip, setTip] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const node = data.evidence;
  const detailed = useStore(s => s.transform[2] > 1.1);
  const background = !data.onRoute;
  const showLabel = !background || detailed || selected || hovered || lit || data.labelled;
  const enter = () => { setHovered(true); window.clearTimeout(timer.current); timer.current = window.setTimeout(() => setTip(true), 140); };
  const leave = () => { setHovered(false); window.clearTimeout(timer.current); setTip(false); };
  return (
    <div className={`network-node ${background ? "is-background" : "is-route"} ${selected ? "is-selected" : ""} ${data.stop ? "is-cited" : ""} ${dimmed ? "is-dimmed" : ""} ${linked ? "is-linked" : ""} ${data.anchor ? "is-anchor" : ""}`}
      style={{ "--node-color": `var(--node-${node.label.toLowerCase()}, var(--muted))`, "--i": data.order ?? 0 } as CSSProperties}
      onMouseEnter={enter} onMouseLeave={leave}>
      <Handle type="target" position={Position.Left} isConnectable={false} />
      <span className="network-node-disc"><NodeGlyph label={node.label} /></span>
      {data.stop && <span className="network-node-citation">{data.stop}</span>}
      <span className="network-node-label" hidden={!showLabel}>{shortLabel(node, 24) || "Comment"}</span>
      <Handle type="source" position={Position.Right} isConnectable={false} />
      <NodeToolbar isVisible={tip && !selected} position={Position.Top} offset={14}>
        <div className="network-tooltip" role="tooltip">
          <span className="network-tooltip-type"><NodeGlyph label={node.label} /><span>{NODE_TYPE_NAMES[node.label] ?? node.label}</span></span>
          <strong>{node.title}</strong>
        </div>
      </NodeToolbar>
    </div>
  );
}
