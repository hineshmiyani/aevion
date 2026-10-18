"use client";

import { useMemo, useState } from "react";
import { ErrorState, Notice } from "@/components/ask/AnswerStates";
import { EvidencePanel } from "@/components/map/EvidencePanel";
import { WorkspaceScreen } from "@/components/WorkspaceScreen";
import { WorkspaceViews, type WorkspaceView } from "@/components/WorkspaceViews";
import { BackIcon } from "@/components/WorkspaceIcons";
import { useTriage } from "@/hooks/use-triage";
import { graphSchema, SCHEMA_ANCHOR, SCHEMA_POSITIONS, triageWalk } from "@/lib/graph-schema";
import sample from "@/lib/triage-sample.json";
import type { EvidencePath, GraphStats, TriageMode, TriageResponse } from "@/lib/types";
import { STARTERS, TriageForm } from "./TriageForm";
import { PendingSteps, TriageSteps } from "./TriageSteps";

function routeStops(data: TriageResponse): string[] {
  const voter = data.component?.via.find(v => v.includes("#") && !v.startsWith("name:"));
  return [voter && "Issue:" + voter, data.component && "Component:" + data.component.key, data.expert && "Person:" + data.expert.login].filter((id): id is string => Boolean(id));
}

export function TriageExperience({ org, stats }: { org: string; stats?: GraphStats }) {
  const { state, triage, reset } = useTriage(org);
  const [highlighted, setHighlighted] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [previous, setPrevious] = useState(sample as unknown as TriageResponse);
  const [view, setView] = useState<WorkspaceView>("answer");
  const shown = state.status === "success" ? state.data : previous;
  const busy = state.status === "loading";
  const idle = state.status === "idle";
  const toggle = (id: string) => setHighlighted(current => current === id ? null : id);
  // The start screen maps the graph model; a starter lights the part of it triage walks.
  // While a triage loads, the map keeps whatever it last showed.
  const [starter, setStarter] = useState<string | null>(null);
  const schema = useMemo(() => ({ evidence: graphSchema(stats), stops: [] as string[], anchor: SCHEMA_ANCHOR }), [stats]);
  const [mapBefore, setMapBefore] = useState<{ evidence: EvidencePath; stops: string[]; anchor?: string }>(schema);
  const map = idle ? schema
    : state.status === "success" ? { evidence: shown.evidence, stops: routeStops(shown), anchor: shown.component ? "Component:" + shown.component.key : undefined }
    : mapBefore;
  const onSchema = map.evidence === schema.evidence;
  const lit = useMemo(() => idle && starter ? triageWalk() : [], [idle, starter]);
  const start = (key: string, mode: TriageMode) => {
    setPrevious(shown);
    setMapBefore(map);
    setStarter(null);
    setHighlighted(null);
    setView("answer");
    void triage(key, mode);
  };
  const goBack = () => { setPrevious(shown); reset(); setHighlighted(null); setView("answer"); };
  return <div className="evidence-workspace">
    <aside className={"workspace-sidebar triage-sidebar " + (idle ? "is-start" : "")}>
      <WorkspaceScreen screen={idle ? "start" : "answer"} startFocus="#issue-key">{idle ? <div className="question-entry"><TriageForm busy={busy} idle={idle} onTriage={start} onPreview={setStarter} /></div> : <>
        <header className="answer-header">
          <button type="button" className="ghost-button back-button" aria-label="Back to issues" title="Back to issues" onClick={goBack}><BackIcon /></button>
          <h1 className="answer-title is-key">{state.issueKey}</h1>
        </header>
        <WorkspaceViews view={view} onView={setView} evidence={shown.evidence} citations={[]} cypher={shown.cypher} params={{ key: shown.issue.key, repo: shown.issue.context_repo ?? shown.issue.repo }} highlighted={highlighted} onSelect={id => setHighlighted(id)} onHover={setHovered}>
          <section aria-label="Triage result" aria-live="polite" aria-busy={busy}>
            <h2 className="sr-only">Triage findings</h2>
            {state.status === "loading" && <PendingSteps applying={state.mode === "apply"} />}
            {state.status === "error" && state.notFound && <Notice title={state.issueKey + " isn't in the graph."}><p>Aevion reads issues from the last 12 months in the {org} organisation&apos;s public repositories, plus the sandbox. Check the key, or try one of these:</p><ul className="notice-starters">{STARTERS.slice(0, 3).map(s => <li key={s.key}><button type="button" className="text-action" onClick={() => start(s.key, "dry_run")}>{s.key}</button></li>)}</ul></Notice>}
            {state.status === "error" && !state.notFound && <ErrorState title="Couldn't triage that issue" retryLabel="Triage again" message={state.error} retryAfterSeconds={state.retryAfterSeconds} onRetry={() => start(state.issueKey, "dry_run")} />}
            {state.status === "success" && <>
              <TriageSteps data={state.data} />
              <p className="answer-meta">{state.data.sample ? "Recorded demo · no actions are sent" : state.data.mode === "dry_run" ? "Preview · proposed actions only" : "Sandbox action results"}</p>
            </>}
          </section>
        </WorkspaceViews>
      </>}</WorkspaceScreen>
    </aside>
    <div className="workspace-map"><EvidencePanel evidence={map.evidence} citations={[]} stops={map.stops} highlighted={highlighted} hovered={idle ? null : hovered} onHover={setHovered} onSelect={toggle} label={onSchema ? "Graph model" : "Evidence map for this triage"} labelled={onSchema} positions={onSchema ? SCHEMA_POSITIONS : undefined} routeLabel="route from a similar issue, through the code its fix changed, to who knows it" anchor={map.anchor} lit={lit} revision={state.status === "success" ? state.issueKey : idle ? "schema" : "pending"} busy={busy} preview={idle} /></div>
  </div>;
}
