"use client";

import type { ReactNode } from "react";
import { AnimatePresence, motion, useIsPresent, useReducedMotion } from "motion/react";
import { EvidenceTrail } from "@/components/ask/EvidenceTrail";
import { CypherList } from "@/components/map/CypherList";
import type { Citation, EvidencePath, ToolCall } from "@/lib/types";

export type WorkspaceView = "answer" | "path" | "cypher";
type Props = {
  view: WorkspaceView; onView: (view: WorkspaceView) => void; evidence: EvidencePath;
  citations: Citation[]; cypher: string[]; calls?: ToolCall[]; params?: Record<string, unknown>;
  highlighted: string | null; onSelect: (id: string) => void; onHover?: (id: string | null) => void; children: ReactNode;
  /** Shown at the right end of the tab row, outside the tablist. */
  actions?: ReactNode;
};

function TabPanel({ view, children }: { view: WorkspaceView; children: ReactNode }) {
  const present = useIsPresent();
  const reduced = useReducedMotion();
  return <motion.div role="tabpanel" id={"content-" + view} aria-labelledby={"view-" + view}
    className="workspace-content" tabIndex={0} inert={!present} aria-hidden={!present || undefined}
    initial={{ opacity: reduced ? 1 : 0, y: reduced ? 0 : 8 }} animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, transition: { duration: reduced ? 0 : 0.08 } }}
    transition={{ duration: reduced ? 0 : 0.24, ease: [0.2, 0.7, 0.2, 1] }}>
    {children}
  </motion.div>;
}

export function WorkspaceViews({ view, onView, evidence, citations, cypher, calls, params, highlighted, onSelect, onHover, children, actions }: Props) {
  const reduced = useReducedMotion();
  const tabs: { id: WorkspaceView; label: string; count?: number }[] = [
    { id: "answer", label: "Answer" },
    { id: "path", label: "Path", count: evidence.nodes.length },
    { id: "cypher", label: "Cypher", count: cypher.length },
  ];
  return <>
    <div className="workspace-tabs">
    <div role="tablist" aria-label="Answer views" className="workspace-tablist">
      {tabs.map(({ id, label, count }, index) => <button type="button" key={id} role="tab" aria-label={count === undefined ? label : label + " (" + count + ")"} id={"view-" + id} aria-selected={view === id} aria-controls={"content-" + id} tabIndex={view === id ? 0 : -1} onClick={() => onView(id)} onKeyDown={event => {
        const offset = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
        if (!offset && event.key !== "Home" && event.key !== "End") return;
        event.preventDefault();
        const next = event.key === "Home" ? tabs[0] : event.key === "End" ? tabs[tabs.length - 1] : tabs[(index + offset + tabs.length) % tabs.length];
        onView(next.id);
        document.getElementById("view-" + next.id)?.focus();
      }}>{label}{count !== undefined && <span className="workspace-tab-count" aria-hidden="true">{count}</span>}
        {view === id && <motion.span layoutId="workspace-tab-indicator" className="workspace-tab-indicator" aria-hidden="true" transition={reduced ? { duration: 0 } : { type: "spring", stiffness: 520, damping: 40 }} />}
      </button>)}
    </div>
    {actions && <div className="workspace-tab-actions">{actions}</div>}
    </div>
    <div className="workspace-panels"><AnimatePresence initial={false} mode="wait"><TabPanel key={view} view={view}>
      {view === "answer" && children}
      {view === "path" && <EvidenceTrail evidence={evidence} citations={citations} highlighted={highlighted} onSelect={onSelect} onHover={onHover} />}
      {view === "cypher" && (cypher.length ? <CypherList cypher={cypher} calls={calls} params={params} /> : <p className="answer-meta">No graph queries for this answer.</p>)}
    </TabPanel></AnimatePresence></div>
  </>;
}
