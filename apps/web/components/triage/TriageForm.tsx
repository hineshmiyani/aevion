"use client";

import { useState, type CSSProperties, type FormEvent } from "react";

import { ArrowIcon } from "@/components/WorkspaceIcons";

import type { TriageMode } from "@/lib/types";

export const SANDBOX = "hineshmiyani/aevion-sandbox";

// Real open issues from the graph, plus a sandbox issue Aevion has already acted on.
export const STARTERS = [
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
  /** The starter being pointed at, so the map can light where it lands. */
  onPreview?: (issueKey: string | null) => void;
};

export function TriageForm({ busy, onTriage, idle, onPreview }: TriageFormProps) {
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
        className={`font-serif leading-[1.04] font-semibold tracking-[-0.015em] text-balance ${idle ? "text-display" : "text-2xl"}`}
      >
        Which issue needs attention?
      </h1>

      <form onSubmit={submit} className="triage-form mt-7 space-y-3">
        <div>
          <label htmlFor="issue-key" className="sr-only">
            Issue
          </label>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
            <input
              id="issue-key"
              value={issueKey}
              onChange={(e) => setIssueKey(e.target.value)}
              placeholder="FalkorDB/FalkorDB#3357"
              autoComplete="off"
              spellCheck={false}
              aria-describedby="issue-key-hint"
              aria-invalid={key.length > 0 && !valid}
              className="min-h-12 flex-1 border border-rule-strong bg-surface px-3 font-mono text-ui text-ink transition-colors placeholder:text-muted focus:border-path focus:outline-none"
            />
            <button
              type="submit"
              disabled={busy || !valid}
              className="min-h-12 min-w-28 bg-ink px-5 font-medium text-paper transition-[opacity,transform] duration-150 hover:opacity-90 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {busy ? "Triaging…" : effectiveMode === "apply" ? "Triage and act" : "Triage"}
            </button>
          </div>
          <p id="issue-key-hint" className="sr-only">
            An issue key, owner/repo#number. On FalkorDB&apos;s repos Aevion only shows what it would do.
          </p>
        </div>

        {/* Quiet custom radios over the real inputs, so keyboard and screen readers still get radios. */}
        <fieldset className="mode-switch">
          <legend className="sr-only">What Aevion should do</legend>
          <div className="mode-track">
            <label className="mode-option">
              <input type="radio" name="mode" value="dry_run" checked={effectiveMode === "dry_run"} onChange={() => setMode("dry_run")} />
              <span className="mode-dot" aria-hidden /><span>Show what it would do</span>
            </label>
            <label className="mode-option">
              <input
                type="radio"
                name="mode"
                value="apply"
                checked={effectiveMode === "apply"}
                disabled={!onSandbox}
                onChange={() => setMode("apply")}
                aria-describedby="apply-hint"
              />
              <span className="mode-dot" aria-hidden /><span>Act on the issue</span>
            </label>
          </div>
          <p id="apply-hint" className="mode-hint">
            {onSandbox ? "Labels it and posts the reply, once per issue." : "Only on the sandbox repo. FalkorDB's repos are read-only."}
          </p>
        </fieldset>
      </form>

      {idle && (
        <div className="suggestions">
          <h2>Try an issue</h2>
          <ul className="question-suggestions">
            {STARTERS.slice(0, 3).map((starter, i) => (
              <li key={starter.key} style={{ "--i": i } as CSSProperties}>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => start(starter.key, "mode" in starter ? starter.mode : "dry_run")}
                  onMouseEnter={() => onPreview?.(starter.key)}
                  onMouseLeave={() => onPreview?.(null)}
                  onFocus={() => onPreview?.(starter.key)}
                  onBlur={() => onPreview?.(null)}
                >
                  <span className="question-label font-mono">{starter.key}</span>
                  <span className="question-note">{starter.note}</span>
                  <span className="question-chevron"><ArrowIcon /></span>
                </button>
              </li>
            ))}
          </ul>
          <a href={"https://github.com/" + SANDBOX + "/issues/new"} target="_blank" rel="noreferrer" className="sandbox-link">Open a new issue on the sandbox ↗</a>
        </div>
      )}
    </section>
  );
}
