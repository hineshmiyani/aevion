// Loading and error states for the ask view. (The empty state is the starter list.)

export function AnswerSkeleton({ question }: { question: string }) {
  return (
    <div aria-busy="true" className="max-w-[68ch]">
      <p className="mb-5 font-serif text-xl leading-snug text-muted">{question}</p>
      <p className="mb-4 text-sm text-muted">Following the graph…</p>
      <div className="space-y-3">
        {[96, 88, 92, 64].map((w) => (
          <div key={w} className="h-3.5 animate-pulse bg-rule" style={{ width: `${w}%` }} />
        ))}
      </div>
    </div>
  );
}

type ErrorStateProps = { message: string; retryAfterSeconds?: number; onRetry: () => void };

export function ErrorState({ message, retryAfterSeconds, onRetry }: ErrorStateProps) {
  return (
    <div role="alert" className="max-w-[68ch] border border-danger/40 bg-danger-soft px-4 py-3 text-sm">
      <p className="font-medium text-danger">No answer this time</p>
      <p className="mt-1 text-ink">
        {message}
        {retryAfterSeconds ? ` Ask again in about ${Math.max(1, Math.ceil(retryAfterSeconds / 60))} min.` : ""}
      </p>
      {!retryAfterSeconds && (
        <button type="button" onClick={onRetry} className="mt-2 min-h-11 font-medium text-danger underline underline-offset-2">
          Ask again
        </button>
      )}
    </div>
  );
}
