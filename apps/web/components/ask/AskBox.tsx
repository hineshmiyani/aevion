"use client";

import { useState, type FormEvent, type KeyboardEvent } from "react";

import { HERO_QUESTIONS } from "@/lib/hero-questions";

type AskBoxProps = {
  onAsk: (question: string) => void;
  busy: boolean;
  /** Show the starter questions (only before the first question). */
  showStarters: boolean;
};

export function AskBox({ onAsk, busy, showStarters }: AskBoxProps) {
  const [question, setQuestion] = useState("");

  const submit = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    onAsk(trimmed);
    setQuestion(""); // the answer heading now shows what was asked
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    submit(question);
  };

  // Enter asks; Shift+Enter adds a line break.
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit(question);
    }
  };

  return (
    <div>
      <h1 id="ask-heading" className="mb-4 font-serif text-3xl leading-tight font-semibold tracking-tight sm:text-4xl">
        Ask the FalkorDB graph
      </h1>
      <form onSubmit={onSubmit} className="flex items-stretch gap-2">
        <textarea
          id="question"
          rows={2}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={onKeyDown}
          maxLength={500}
          placeholder="Ask about people, decisions or recent changes"
          aria-labelledby="ask-heading"
          aria-describedby="question-hint"
          className="min-h-14 flex-1 resize-y rounded-md border border-rule-strong bg-surface px-3 py-2.5 font-serif text-lg text-ink placeholder:font-sans placeholder:text-base placeholder:text-muted focus:border-path focus:outline-none"
        />
        <button
          type="submit"
          disabled={busy || !question.trim()}
          className="min-w-20 rounded-md bg-ink px-5 text-sm font-medium text-paper transition-opacity hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-35"
        >
          {busy ? "Asking…" : "Ask"}
        </button>
      </form>
      <p id="question-hint" className="mt-1.5 text-xs text-muted">
        Enter to ask, Shift+Enter for a new line.
      </p>

      {showStarters && (
        <div className="mt-6">
          <h2 className="mb-2 text-sm text-muted">Or start with one of these</h2>
          <ul className="divide-y divide-rule border-y border-rule">
            {HERO_QUESTIONS.map(({ kind, question: starter }) => (
              <li key={kind}>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => submit(starter)}
                  className="flex min-h-11 w-full items-baseline gap-4 py-2.5 text-left transition-colors hover:text-path disabled:opacity-50"
                >
                  <span className="w-16 shrink-0 text-xs text-muted">{kind}</span>
                  <span className="font-serif text-[17px]">{starter}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
