"use client";

import { useAsk } from "@/hooks/use-ask";

import { AnswerPanel } from "./AnswerPanel";
import { AnswerSkeleton, ErrorState } from "./AnswerStates";
import { AskBox } from "./AskBox";

/** The ask flow: question box (with starters until the first question), then the result. */
export function AskExperience({ org }: { org: string }) {
  const { state, ask } = useAsk(org);

  return (
    <div className="space-y-12">
      <AskBox onAsk={ask} busy={state.status === "loading"} showStarters={state.status === "idle"} />
      <section aria-live="polite" aria-label="Answer">
        {state.status === "loading" && <AnswerSkeleton question={state.question} />}
        {state.status === "error" && (
          <ErrorState message={state.error} retryAfterSeconds={state.retryAfterSeconds} onRetry={() => ask(state.question)} />
        )}
        {state.status === "success" && <AnswerPanel question={state.question} data={state.data} />}
      </section>
    </div>
  );
}
