"use client";

import { useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { EvidencePanel } from "@/components/map/EvidencePanel";
import { useAskStream } from "@/hooks/use-ask-stream";
import { HERO_QUESTIONS } from "@/lib/hero-questions";
import type { AskResponse, GraphStats } from "@/lib/types";

import { AnswerText } from "./AnswerText";
import { ErrorState } from "./AnswerStates";
import { ProgressLog } from "./ProgressLog";

const fmt = new Intl.NumberFormat("en-US");

function answerMeta(data: AskResponse): string {
  const ms = data.elapsed_ms;
  const time = ms == null ? "" : ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
  if (data.sample) return "A recorded sample answer. Set AEVION_API_URL to ask live.";
  if (data.cached) return time ? `Answered from the graph in ${time}, cached` : "Answered from the graph, cached";
  const calls = data.tool_calls.length;
  return `Answered in ${time} with ${calls} graph ${calls === 1 ? "query" : "queries"}, tracing ${data.evidence.edges.length} edges`;
}

type Props = { org: string; stats: GraphStats; featured: { question: string; data: AskResponse } };

/** Ask: the question on the left, the evidence map beside it. Before the first question the
 * map already shows a real answer, so the graph is visibly working from the first second. */
export function AskExperience({ org, stats, featured }: Props) {
  const { state, ask, show } = useAskStream(org);
  const [question, setQuestion] = useState("");
  const box = useRef<HTMLTextAreaElement>(null);
  const [highlighted, setHighlighted] = useState<string | null>(null);
  const busy = state.status === "working";
  const idle = state.status === "idle";

  // The map shows the current answer, or the featured one before anything is asked.
  const shown = state.status === "success" ? state.data : idle ? featured.data : null;
  const nodes = useMemo(() => new Map((shown?.evidence.nodes ?? []).map((n) => [n.id, n])), [shown]);

  const submit = (text: string) => {
    const trimmed = text.trim();
    if (busy) return;
    if (!trimmed) {
      box.current?.focus(); // an empty ask points at the box instead of doing nothing
      return;
    }
    setHighlighted(null);
    setQuestion("");
    void ask(trimmed);
  };
  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    submit(question);
  };
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit(question);
    }
  };
  const toggle = (id: string) => setHighlighted((current) => (current === id ? null : id));

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-x-12 gap-y-10 lg:grid-cols-[minmax(0,34rem)_minmax(0,1fr)]">
      <div className="min-w-0">
        <h1 className={`font-serif leading-[1.04] font-semibold tracking-[-0.015em] text-balance ${idle ? "text-[clamp(2.25rem,4.4vw,3.5rem)]" : "text-2xl"}`}>
          Ask how FalkorDB works.
        </h1>
        {idle && (
          <p className="mt-4 max-w-[38ch] font-serif text-xl leading-snug text-muted">
            Every answer comes with the path through the project&apos;s graph that proves it.
          </p>
        )}

        <form onSubmit={onSubmit} className="mt-7">
          <label htmlFor="question" className="text-sm font-medium">
            Your question
          </label>
          <div className="mt-1.5 flex items-stretch gap-2">
            <textarea
              id="question"
              ref={box}
              rows={2}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={onKeyDown}
              maxLength={500}
              placeholder="Who knows the query planner? Why was this changed?"
              aria-describedby="question-hint"
              className="min-h-14 flex-1 resize-y border border-rule-strong bg-surface px-3 py-2.5 font-serif text-lg text-ink transition-colors placeholder:font-sans placeholder:text-base placeholder:text-muted focus:border-path focus:outline-none"
            />
            <button
              type="submit"
              disabled={busy}
              className="min-w-20 bg-ink px-5 font-medium text-paper transition-[opacity,transform] duration-150 hover:opacity-90 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {busy ? "Asking…" : "Ask"}
            </button>
          </div>
          <p id="question-hint" className="mt-1.5 text-xs text-muted">
            Enter to ask, Shift+Enter for a new line.
          </p>
        </form>

        {idle && (
          <>
            <p className="mt-6 text-sm text-muted">
              {stats.sample ? "The graph (recorded): " : "The graph right now: "}
              <strong className="font-semibold text-ink tabular-nums">{fmt.format(stats.nodes)}</strong> nodes and{" "}
              <strong className="font-semibold text-ink tabular-nums">{fmt.format(stats.edges)}</strong> edges from{" "}
              <strong className="font-semibold text-ink tabular-nums">{stats.repos}</strong> repositories, including{" "}
              <strong className="font-semibold text-ink tabular-nums">{fmt.format(stats.pull_requests)}</strong> pull requests and{" "}
              <strong className="font-semibold text-ink tabular-nums">{fmt.format(stats.decisions)}</strong> decisions.
            </p>
            <h2 className="mt-9 mb-2 text-sm font-medium">Try a question</h2>
            <ul className="divide-y divide-rule border-y border-rule">
              {HERO_QUESTIONS.map(({ kind, question: starter }) => (
                <li key={kind}>
                  <button
                    type="button"
                    onClick={() => submit(starter)}
                    className="group flex min-h-12 w-full items-baseline gap-4 py-2.5 text-left transition-colors hover:bg-surface"
                  >
                    <span className="w-20 shrink-0 text-sm text-muted">{kind}</span>
                    <span className="font-serif text-[17px] leading-snug text-ink decoration-path underline-offset-4 group-hover:underline">
                      {starter}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}

        {!idle && (
          <article aria-live="polite" aria-busy={busy} className="mt-10">
            <h2 className="font-serif text-[22px] leading-snug text-muted">{state.question}</h2>
            <div className="mt-4">
              <ProgressLog steps={state.steps} working={busy} />
            </div>
            {state.status === "success" && (
              <div className="arrive mt-6">
                <AnswerText
                  text={state.data.answer}
                  citations={state.data.citations}
                  nodes={nodes}
                  highlighted={highlighted}
                  onCite={(id) => toggle(id)}
                />
                <p className="mt-6 border-t border-rule pt-3 text-sm text-muted">{answerMeta(state.data)}</p>
              </div>
            )}
            {state.status === "error" && (
              <div className="mt-6">
                <ErrorState message={state.error} retryAfterSeconds={state.retryAfterSeconds} onRetry={() => ask(state.question)} />
              </div>
            )}
          </article>
        )}
      </div>

      <div className="min-w-0 lg:sticky lg:top-6 lg:h-[calc(100dvh-9rem)] lg:min-h-[520px] lg:self-start">
        {shown ? (
          <EvidencePanel
            key={state.status === "success" ? state.question : "featured"}
            evidence={shown.evidence}
            citations={shown.citations}
            cypher={shown.cypher}
            highlighted={highlighted}
            onSelect={toggle}
            label={idle ? "Evidence map for a recent answer" : "Evidence map for this answer"}
            caption={
              idle ? (
                <p className="text-sm text-muted">
                  Traced from a real answer: <span className="font-serif text-base text-ink">{featured.question}</span>{" "}
                  <button type="button" onClick={() => show(featured.question, featured.data)} className="font-medium text-path underline underline-offset-4">
                    Read the answer
                  </button>
                </p>
              ) : null
            }
          />
        ) : (
          <div className="survey-grid flex h-full min-h-[340px] items-center justify-center border border-rule" aria-hidden>
            <p className="working text-sm text-muted">Tracing the route through the graph…</p>
          </div>
        )}
      </div>
    </div>
  );
}
