"use client";

import { useState, type FormEvent } from "react";

import type { TriageMode } from "@/lib/types";

export const SANDBOX = "hineshmiyani/aevion-sandbox";

// Real open issues from the graph, plus a sandbox issue Aevion has already acted on.
const STARTERS = [
  { key: "FalkorDB/FalkorDB#3357", note: "UDF reload races concurrent queries" },
  { key: "FalkorDB/falkordb-py#306", note: "Python client errors during failovers" },
  { key: "FalkorDB/GraphRAG-SDK#344", note: "SDK incompatibilities with FalkorDB 6" },
  { key: `${SANDBOX}#37`, note: "Sandbox: see what Aevion did", mode: "apply" as const },
] as const;

const ISSUE_KEY = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+#[0-9]+$/;

type TriageFormProps = {
  busy: boolean;
  onTriage: (issueKey: string, mode: TriageMode) => void;
  showStarters: boolean;
};

export function TriageForm({ busy, onTriage, showStarters }: TriageFormProps) {
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
      <h1 id="triage-heading" className="mb-2 font-serif text-[clamp(1.75rem,3vw,2.25rem)] leading-tight font-semibold">
        Triage an issue
      </h1>
      <p className="mb-6 max-w-[62ch] text-sm text-muted">
        Aevion finds similar issues, follows the PRs that fixed them to the code they changed, and names who knows that
        code. On FalkorDB&apos;s repos it only shows what it would do. On{" "}
        <a href={`https://github.com/${SANDBOX}`} className="text-ink underline decoration-rule-strong underline-offset-2 hover:decoration-path">
          our sandbox repo
        </a>{" "}
        it acts.
      </p>

      <form onSubmit={submit} className="space-y-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
          <label htmlFor="issue-key" className="sr-only">
            Issue key
          </label>
          <input
            id="issue-key"
            value={issueKey}
            onChange={(e) => setIssueKey(e.target.value)}
            placeholder="FalkorDB/FalkorDB#3357"
            autoComplete="off"
            spellCheck={false}
            aria-describedby="issue-key-hint"
            aria-invalid={key.length > 0 && !valid}
            className="min-h-12 flex-1 rounded-md border border-rule-strong bg-surface px-3 font-mono text-base text-ink placeholder:text-muted focus:border-path focus:outline-none"
          />
          <button
            type="submit"
            disabled={busy || !valid}
            className="min-h-12 min-w-28 rounded-md bg-ink px-5 text-sm font-medium text-paper transition-opacity hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-35"
          >
            {busy ? "Triaging…" : effectiveMode === "apply" ? "Triage and act" : "Triage"}
          </button>
        </div>
        <p id="issue-key-hint" className="text-xs text-muted">
          An issue key: <span className="font-mono">owner/repo#number</span>.
        </p>

        <fieldset className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
          <legend className="sr-only">Mode</legend>
          <label className="inline-flex min-h-11 items-center gap-2">
            <input type="radio" name="mode" value="dry_run" checked={effectiveMode === "dry_run"} onChange={() => setMode("dry_run")} className="accent-[var(--path)]" />
            Dry run: show what it would do
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
            {onSandbox ? "Labels it and posts the reply, once per issue." : "Acting is only allowed on the sandbox repo."}
          </span>
        </fieldset>
      </form>

      {showStarters && (
        <div className="mt-8">
          <h2 className="mb-2 text-sm text-muted">Or try one of these</h2>
          <ul className="divide-y divide-rule border-y border-rule">
            {STARTERS.map((starter) => (
              <li key={starter.key}>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => start(starter.key, "mode" in starter ? starter.mode : "dry_run")}
                  className="flex min-h-12 w-full flex-wrap items-baseline gap-x-4 gap-y-0.5 py-2.5 text-left hover:bg-surface disabled:opacity-50"
                >
                  <span className="font-mono text-sm text-ink">{starter.key}</span>
                  <span className="text-sm text-muted">{starter.note}</span>
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
              className="text-ink underline decoration-rule-strong underline-offset-2 hover:decoration-path"
            >
              open a new issue on the sandbox
            </a>
            : Aevion triages it on its own within about 10 seconds.
          </p>
        </div>
      )}
    </section>
  );
}
