"use client";

import { AnswerSkeleton, ErrorState } from "@/components/ask/AnswerStates";
import { useTriage } from "@/hooks/use-triage";

import { TriageForm } from "./TriageForm";
import { TriageResult } from "./TriageResult";

export function TriageExperience({ org }: { org: string }) {
  const { state, triage } = useTriage(org);
  const busy = state.status === "loading";

  return (
    <div className="space-y-12">
      <TriageForm busy={busy} onTriage={triage} showStarters={state.status === "idle"} />
      <section aria-label="Triage result" aria-live="polite">
        {state.status === "loading" && (
          <AnswerSkeleton question={state.mode === "apply" ? `Triaging and acting on ${state.issueKey}…` : `Triaging ${state.issueKey}…`} />
        )}
        {state.status === "error" && (
          <ErrorState message={state.error} retryAfterSeconds={state.retryAfterSeconds} onRetry={() => triage(state.issueKey, "dry_run")} />
        )}
        {state.status === "success" && <TriageResult data={state.data} />}
      </section>
    </div>
  );
}
