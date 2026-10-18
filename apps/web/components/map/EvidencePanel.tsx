"use client";

import type { Citation, EvidencePath } from "@/lib/types";
import { EvidenceMap } from "./EvidenceMap";

type Props = {
  evidence: EvidencePath; citations: Citation[]; stops?: string[];
  highlighted: string | null; onSelect: (id: string) => void; label: string;
  hovered?: string | null; onHover?: (id: string | null) => void;
  routeLabel?: string; anchor?: string; revision?: string; busy?: boolean; preview?: boolean; lit?: string[]; labelled?: boolean; positions?: Record<string, [number, number]>;
};

export function EvidencePanel({ evidence, citations, stops, highlighted, hovered, onHover, onSelect, label, routeLabel, anchor, revision, busy, preview, lit, labelled, positions }: Props) {
  const routeStops = stops ?? [...citations].sort((a, b) => a.n - b.n).map(c => c.node_id);
  return <section aria-label={label} className="evidence-panel"><div className="evidence-map-slot"><EvidenceMap evidence={evidence} stops={routeStops} highlighted={highlighted} hovered={hovered} onHover={onHover} onSelect={onSelect} label={label} routeLabel={routeLabel} anchor={anchor} revision={revision} busy={busy} preview={preview} lit={lit} labelled={labelled} positions={positions} /></div></section>;
}
