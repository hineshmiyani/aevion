"use client";

import { useState } from "react";

import { ErrorState, Notice } from "@/components/ask/AnswerStates";
import { EvidencePanel } from "@/components/map/EvidencePanel";
import { useTriage } from "@/hooks/use-triage";
import type { TriageResponse } from "@/lib/types";

import { STARTERS, TriageForm } from "./TriageForm";
import { PendingSteps, TriageSteps } from "./TriageSteps";

/** The route the map draws for a triage: from a similar issue whose fix changed the chosen
 * area of the code, to that area, to the person who knows it. The map follows the graph's own
 * edges between them (issue, fixing pull request, file, area). */
function routeStops(data: TriageResponse): string[] {
  const voter = data.component?.via.find((v) => v.includes("#") && !v.startsWith("name:"));
  return [
    voter && `Issue:${voter}`,
    data.component && `Component:${data.component.key}`,
    data.expert && `Person:${data.expert.login}`,
  ].filter((id): id is string => Boolean(id));
}

export function TriageExperience({ org }: { org: string }) {
  const { state, triage } = useTriage(org);
  const [highlighted, setHighlighted] = useState<string | null>(null);
  const busy = state.status === "loading";
  const idle = state.status === "idle";
  const toggle = (id: string) => setHighlighted((current) => (current === id ? null : id));

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-x-12 gap-y-10 lg:grid-cols-[minmax(0,34rem)_minmax(0,1fr)]">
      <div className="min-w-0">
        <TriageForm busy={busy} idle={idle} onTriage={(key, mode) => {
            setHighlighted(null);
            void triage(key, mode);
          }} />
        <section aria-label="Triage result" aria-live="polite" aria-busy={busy} className={idle ? "" : "mt-10"}>
          {state.status === "loading" && (
            <>
              <p className="mb-4 flex items-center gap-2.5 text-sm text-muted">
                <span aria-hidden className="working inline-block size-2 bg-path" />
                {state.mode === "apply" ? `Triaging and acting on ${state.issueKey}` : `Triaging ${state.issueKey}`}, usually about ten seconds.
              </p>
              <PendingSteps applying={state.mode === "apply"} />
            </>
          )}
          {state.status === "error" && state.notFound && (
            <Notice title={`${state.issueKey} isn't in the graph.`}>
              <p>
                Aevion reads issues from the last 12 months in the {org} organisation&apos;s public repositories, plus the sandbox.
                Check the key, or try one of these:
              </p>
              <ul className="mt-2 flex flex-wrap gap-2">
                {STARTERS.map((s) => (
                  <li key={s.key}>
                    <button
                      type="button"
                      onClick={() => triage(s.key, "mode" in s ? s.mode : "dry_run")}
                      className="min-h-11 border border-rule-strong bg-paper px-2.5 font-mono text-[13px] text-ink transition-colors hover:border-path"
                    >
                      {s.key}
                    </button>
                  </li>
                ))}
              </ul>
            </Notice>
          )}
          {state.status === "error" && !state.notFound && (
            <ErrorState
              title="Couldn't triage that issue"
              retryLabel="Triage again"
              message={state.error}
              retryAfterSeconds={state.retryAfterSeconds}
              onRetry={() => triage(state.issueKey, "dry_run")}
            />
          )}
          {state.status === "success" && <TriageSteps key={state.issueKey} data={state.data} />}
          {state.status === "success" && state.data.sample && (
            <p className="mt-6 text-xs text-muted">This is a recorded sample triage. Set AEVION_API_URL to triage live.</p>
          )}
        </section>
      </div>

      <div className="min-w-0 lg:sticky lg:top-6 lg:h-[calc(100dvh-9rem)] lg:min-h-[520px] lg:self-start">
        {state.status === "success" ? (
          <EvidencePanel
            key={state.issueKey}
            evidence={state.data.evidence}
            citations={[]}
            cypher={state.data.cypher}
            params={{ key: state.data.issue.key, repo: state.data.issue.context_repo ?? state.data.issue.repo }}
            stops={routeStops(state.data)}
            highlighted={highlighted}
            onSelect={toggle}
            label="Evidence map for this triage"
            routeLabel="route from a similar issue, through the code its fix changed, to who knows it"
          />
        ) : (
          <div className="survey-grid flex h-full min-h-[340px] items-center justify-center border border-rule p-8 text-center" aria-hidden>
            <p className="flex max-w-xs items-center gap-2.5 text-sm text-muted">
              {busy && <span aria-hidden className="working inline-block size-2 shrink-0 bg-path" />}
              {busy ? "Tracing the route through the graph" : "The route from similar issues to the code and the people who know it appears here."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
