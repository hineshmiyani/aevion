"use client";

import { useState, type ReactNode } from "react";

import { EvidenceTrail } from "@/components/ask/EvidenceTrail";
import type { Citation, EvidencePath } from "@/lib/types";

import { EvidenceMap } from "./EvidenceMap";

type Tab = "map" | "path" | "cypher";

type EvidencePanelProps = {
  evidence: EvidencePath;
  citations: Citation[];
  cypher: string[];
  /** Route stops in order; defaults to the citations. */
  stops?: string[];
  highlighted: string | null;
  onSelect: (nodeId: string) => void;
  label: string;
  routeLabel?: string;
  caption?: ReactNode;
};

/** The answer's evidence three ways: the map (default), the path as text, and the Cypher. */
export function EvidencePanel({ evidence, citations, cypher, stops, highlighted, onSelect, label, routeLabel, caption }: EvidencePanelProps) {
  const [tab, setTab] = useState<Tab>("map");
  const routeStops = stops ?? [...citations].sort((a, b) => a.n - b.n).map((c) => c.node_id);
  // An answer that didn't touch the graph has no path or queries: those tabs aren't offered.
  const tabs: { id: Tab; name: string }[] = [
    { id: "map", name: "Map" },
    ...(evidence.nodes.length ? [{ id: "path" as const, name: `Path (${evidence.nodes.length})` }] : []),
    ...(cypher.length ? [{ id: "cypher" as const, name: `Cypher (${cypher.length})` }] : []),
  ];

  return (
    <section aria-label={label} className="flex h-full min-h-0 flex-col">
      {caption && <div className="mb-3">{caption}</div>}
      <div role="tablist" aria-label="Evidence views" className="mb-3 flex gap-1 border-b border-rule">
        {tabs.map(({ id, name }) => (
          <button
            key={id}
            role="tab"
            id={`tab-${id}`}
            aria-selected={tab === id}
            aria-controls={`panel-${id}`}
            tabIndex={tab === id ? 0 : -1}
            onClick={() => setTab(id)}
            onKeyDown={(e) => {
              const i = tabs.findIndex((t) => t.id === tab);
              if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
                e.preventDefault();
                const next = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length].id;
                setTab(next);
                document.getElementById(`tab-${next}`)?.focus();
              }
            }}
            className={`-mb-px min-h-11 border-b-2 px-3 text-sm transition-colors ${
              tab === id ? "border-path font-medium text-ink" : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {name}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="min-h-0 flex-1">
        {tab === "map" && (
          <div className="flex h-[min(105vw,560px)] flex-col lg:h-full lg:min-h-[340px]">
            <EvidenceMap evidence={evidence} stops={routeStops} highlighted={highlighted} onSelect={onSelect} label={label} routeLabel={routeLabel} />
          </div>
        )}
        {tab === "path" && (
          <div className="h-full overflow-y-auto pr-1">
            <EvidenceTrail evidence={evidence} citations={citations} highlighted={highlighted} />
          </div>
        )}
        {tab === "cypher" && (
          <div className="h-full space-y-3 overflow-y-auto pr-1">
            <p className="text-sm text-muted">The read-only queries that ran against FalkorDB for this answer.</p>
            {cypher.map((query, i) => (
              <pre key={i} className="overflow-x-auto border border-rule bg-surface p-3 font-mono text-[12px] leading-relaxed text-ink">
                {query}
              </pre>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
