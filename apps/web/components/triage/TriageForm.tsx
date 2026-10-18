"use client";

import { useState, type FormEvent } from "react";

import type { TriageMode } from "@/lib/types";

export const SANDBOX = "hineshmiyani/aevion-sandbox";

// Real open issues from the graph, plus a sandbox issue Aevion has already acted on.
const STARTERS = [
  { key: "FalkorDB/FalkorDB#3357", note: "UDF reload races concurrent queries" },
  { key: "FalkorDB/falkordb-py#306", note: "Python client errors during failovers" },
  { key: "FalkorDB/GraphRAG-SDK#344", note: "SDK incompatibilities with FalkorDB 6" },
  { key: `${SANDBOX}#37`, note: "On the sandbox: see what Aevion did", mode: "apply" as const },
] as const;

const ISSUE_KEY = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+#[0-9]+$/;

type TriageFormProps = {
  busy: boolean;
  onTriage: (issueKey: string, mode: TriageMode) => void;
  idle: boolean;
};

export function TriageForm({ busy, onTriage, idle }: TriageFormProps) {
  const [issueKey, setIssueKey] = useState("");
  const [mode, setMode] = useState<TriageMode>("dry_run");
  const key = issueKey.trim();
  const onSandbox = key.startsWith(`${SANDBOX}#`);
  const valid = ISSUE_KEY.test(key);
  const effectiveMode: TriageMode = onSandbox ? mode : "dry_run";

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (valid && !busy) onTriage(key, effectiveMode);
  };
  const start = (starterKey: string, starterMode: TriageMode) => {
    setIssueKey(starterKey);
    setMode(starterMode);
    onTriage(starterKey, starterMode);
  };

  return (
    <section aria-labelledby="triage-heading">
      <h1
        id="triage-heading"
        className={`font-serif leading-[1.04] font-semibold tracking-[-0.015em] text-balance ${idle ? "text-[clamp(2.25rem,4.4vw,3.5rem)]" : "text-2xl"}`}
      >
        Triage an issue.
      </h1>
      {idle && (
        <p className="mt-4 max-w-[42ch] font-serif text-xl leading-snug text-muted">
          Aevion finds issues like it, follows the pull requests that fixed them to the code they changed, and names who
          knows that code.
        </p>
      )}

      <form onSubmit={submit} className="mt-7 space-y-3">
        <div>
          <label htmlFor="issue-key" className="text-sm font-medium">
            Issue
          </label>
          <div className="mt-1.5 flex flex-col gap-2 sm:flex-row sm:items-stretch">
            <input
              id="issue-key"
              value={issueKey}
              onChange={(e) => setIssueKey(e.target.value)}
              placeholder="FalkorDB/FalkorDB#3357"
              autoComplete="off"
              spellCheck={false}
              aria-describedby="issue-key-hint"
              aria-invalid={key.length > 0 && !valid}
              className="min-h-12 flex-1 rounded-md border border-rule-strong bg-surface px-3 font-mono text-[15px] text-ink transition-colors placeholder:text-muted focus:border-path focus:outline-none"
            />
            <button
              type="submit"
              disabled={busy || !valid}
              className="min-h-12 min-w-28 rounded-md bg-ink px-5 font-medium text-paper transition-[opacity,transform] duration-150 hover:opacity-90 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {busy ? "Triaging…" : effectiveMode === "apply" ? "Triage and act" : "Triage"}
            </button>
          </div>
          <p id="issue-key-hint" className="mt-1.5 text-xs text-muted">
            An issue key, owner/repo#number. On FalkorDB&apos;s repos Aevion only shows what it would do.
          </p>
        </div>

        <fieldset className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
          <legend className="sr-only">What Aevion should do</legend>
          <label className="inline-flex min-h-11 items-center gap-2">
            <input type="radio" name="mode" value="dry_run" checked={effectiveMode === "dry_run"} onChange={() => setMode("dry_run")} className="accent-[var(--path)]" />
            Show what it would do
          </label>
          <label className={`inline-flex min-h-11 items-center gap-2 ${onSandbox ? "" : "text-muted"}`}>
            <input
              type="radio"
              name="mode"
              value="apply"
              checked={effectiveMode === "apply"}
              disabled={!onSandbox}
              onChange={() => setMode("apply")}
              aria-describedby="apply-hint"
              className="accent-[var(--path)]"
            />
            Act on the issue
          </label>
          <span id="apply-hint" className="inline-flex items-center text-xs text-muted">
            {onSandbox ? "Labels it and posts the reply, once per issue." : "Only on our sandbox repo."}
          </span>
        </fieldset>
      </form>

      {idle && (
        <div className="mt-9">
          <h2 className="mb-2 text-sm font-medium">Try an issue</h2>
          <ul className="divide-y divide-rule border-y border-rule">
            {STARTERS.map((starter) => (
              <li key={starter.key}>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => start(starter.key, "mode" in starter ? starter.mode : "dry_run")}
                  className="group flex min-h-12 w-full flex-wrap items-baseline gap-x-4 gap-y-0.5 py-2.5 text-left transition-colors hover:bg-surface disabled:opacity-50"
                >
                  <span className="font-mono text-sm text-ink">{starter.key}</span>
                  <span className="text-[15px] text-muted group-hover:text-ink">{starter.note}</span>
                </button>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-sm text-muted">
            Or{" "}
            <a
              href={`https://github.com/${SANDBOX}/issues/new`}
              target="_blank"
              rel="noreferrer"
              className="text-ink underline decoration-rule-strong underline-offset-4 hover:decoration-path"
            >
              open a new issue on the sandbox
            </a>
            . Aevion triages it on its own within about ten seconds.
          </p>
        </div>
      )}
    </section>
  );
}
