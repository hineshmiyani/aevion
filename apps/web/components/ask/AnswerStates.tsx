import type { CSSProperties, ReactNode } from "react";

// Loading and error states for the ask view. (The empty state is the starter list.)

// Two short paragraphs' worth of lines: the shape of an answer, not a spinner in a void.
const PLACEHOLDER = [[100, 94, 97, 58], [96, 89, 42]];

export function AnswerPlaceholder() {
  let line = 0;
  return (
    <div className="answer-loading" aria-hidden="true">
      {PLACEHOLDER.map((widths, p) => (
        <div key={p} className="answer-loading-para">
          {widths.map((w) => <span key={line} className="skeleton-line" style={{ width: `${w}%`, "--i": line++ } as CSSProperties} />)}
        </div>
      ))}
    </div>
  );
}

type ErrorStateProps = {
  message: string;
  retryAfterSeconds?: number;
  onRetry: () => void;
  /** What failed, in the page's own verb: "Couldn't answer that", "Couldn't triage that issue". */
  title?: string;
  retryLabel?: string;
};

export function ErrorState({ message, retryAfterSeconds, onRetry, title = "Couldn't answer that", retryLabel = "Ask again" }: ErrorStateProps) {
  return (
    <div role="alert" className="max-w-[68ch] border border-danger/40 bg-danger-soft px-4 py-3 text-sm">
      <p className="font-medium text-danger">{title}</p>
      <p className="mt-1 text-ink">
        {message}
        {retryAfterSeconds ? ` Try again in about ${Math.max(1, Math.ceil(retryAfterSeconds / 60))} min.` : ""}
      </p>
      {!retryAfterSeconds && (
        <button type="button" onClick={onRetry} className="mt-2 min-h-11 font-medium text-danger underline underline-offset-2">
          {retryLabel}
        </button>
      )}
    </div>
  );
}

/** Nothing went wrong, there's just nothing to show: says why, and what to try instead. */
export function Notice({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div role="status" className="max-w-[68ch] border border-rule-strong bg-surface px-4 py-3 text-sm">
      <p className="font-medium text-ink">{title}</p>
      <div className="mt-1 text-muted">{children}</div>
    </div>
  );
}
