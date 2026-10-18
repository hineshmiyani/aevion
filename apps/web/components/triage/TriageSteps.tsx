import { useState, type ReactNode } from "react";

import { CheckIcon } from "@/components/WorkspaceIcons";

import type { ComponentPick, SimilarIssue, TriageAction, TriageResponse } from "@/lib/types";

import { InlineText, ReplyText } from "./ReplyText";

/*
 * The triage as the agent's steps, in the order it took them. The spine is a route: each
 * marker identifies a step in the timeline. The steps are the real results of one request,
 * revealed in sequence once it returns (the triage API doesn't stream).
 */

const STATUS: Record<TriageAction["status"], string> = {
  proposed: "Proposed", done: "Done", skipped: "Skipped", failed: "Failed",
};

const ACTION_TEXT: Record<TriageAction["type"], (a: TriageAction) => string> = {
  label: (a) => `Add the label “${a.value}”`,
  assign_or_mention: (a) => `Involve ${a.value}`,
  comment: () => "Post the reply",
};

function reasons(component: ComponentPick): string {
  const fixes = component.via.filter((v) => v.includes("#")).length;
  const parts = [
    fixes > 0 && `${fixes} fix${fixes === 1 ? "" : "es"} for similar issues changed it`,
    component.via.some((v) => v.startsWith("name:")) && "its path matches the title",
    component.via.some((v) => v.includes("/") && !v.includes("#")) && "the issue names a file in it",
    component.via.find((v) => v.startsWith("the repo")),
  ].filter(Boolean);
  return parts.join("; ");
}

function Similar({ issue }: { issue: SimilarIssue }) {
  return (
    <li className="py-2">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
        <a href={issue.url} target="_blank" rel="noreferrer" className="triage-key">
          {issue.key}
        </a>
        <span className="text-xs text-muted">
          {issue.state.toLowerCase()}
          {issue.fixed_by.length > 0 && `, fixed by ${issue.fixed_by[0]}`}
        </span>
        {issue.likely_duplicate && <span className="triage-pill is-duplicate">likely duplicate</span>}
      </div>
      <p className="mt-0.5 text-ui leading-snug">
        <InlineText text={issue.title} />
      </p>
    </li>
  );
}

function CopyReply({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button type="button" className="reply-copy" data-copied={copied || undefined} aria-label={copied ? "Copied" : "Copy reply"} onClick={() => {
      void navigator.clipboard?.writeText(text).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500); });
    }}>
      {copied ? <CheckIcon size={13} /> : <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V6a2 2 0 0 1 2-2h9" /></svg>}
      <span className="sr-only" aria-live="polite">{copied ? "Copied" : ""}</span>
    </button>
  );
}

type StepProps = { n: number; title: string; children?: ReactNode; last?: boolean; pending?: boolean };

function Step({ n, title, children, last = false, pending = false }: StepProps) {
  return <li className={"triage-step " + (pending ? "is-pending" : "arrive")} style={pending ? undefined : { animationDelay: String((n - 1) * 100) + "ms" }}>
    <div className="timeline-track" aria-hidden><span className="timeline-number">{n}</span>{!last && <span className="timeline-line" />}</div>
    <div className="timeline-content"><h3>{title}</h3>{children && <div className="timeline-body">{children}</div>}</div>
  </li>;
}

const PENDING = ["Read the issue", "Look for similar issues", "Follow their fixes to the code", "Find who knows it", "Draft a reply"];

/**
 * The same six steps, not yet taken: shown while the triage runs, so the wait has a shape.
 * The API answers in one go, so no step is marked as running; a fade sweeps down them instead.
 */
export function PendingSteps({ applying }: { applying: boolean }) {
  const titles = [...PENDING, applying ? "Act on the sandbox issue" : "Decide what it would do on the sandbox"];
  return (
    <ol aria-label="Steps Aevion is working through" aria-busy="true" className="triage-timeline is-waiting">
      {titles.map((title, i) => (
        <Step key={title} n={i + 1} title={title} last={i === titles.length - 1} pending />
      ))}
    </ol>
  );
}

export function TriageSteps({ data }: { data: TriageResponse }) {
  const similar = [...data.duplicates, ...data.related];
  const applied = data.mode === "apply";
  const context = data.issue.context_repo && data.issue.context_repo !== data.issue.repo ? data.issue.context_repo : null;

  return (
    <ol aria-label="How Aevion triaged this issue" className="mt-2">
      <Step n={1} title="Read the issue">
        <a href={data.issue.url} target="_blank" rel="noreferrer" className="triage-key is-muted">
          {data.issue.key}
        </a>
        <p className="mt-1 font-serif text-xl leading-snug">
          <InlineText text={data.issue.title} />
        </p>
        {context && (
          <p className="mt-1.5 text-sm text-muted">
            Read as an issue about <span className="font-mono text-code text-ink">{context}</span>
            {data.issue.context_reason?.length ? `: ${data.issue.context_reason.join("; ")}` : ""}
          </p>
        )}
      </Step>

      <Step n={2} title={similar.length ? `Found ${similar.length} similar issue${similar.length === 1 ? "" : "s"}` : "Looked for similar issues"}>
        {similar.length ? (
          <ul className="-my-2 divide-y divide-rule">{similar.slice(0, 3).map((s) => <Similar key={s.key} issue={s} />)}</ul>
        ) : (
          <p className="text-sm text-muted">None in the graph look like it.</p>
        )}
      </Step>

      <Step n={3} title="Followed their fixes to the code">
        {data.component ? (
          <>
            <p>
              <span className="font-mono text-ui">{data.component.name}</span>{" "}
              <span
                title={data.component.strength === "weak" ? "Little in the graph points here, so treat it as a guess." : undefined}
                className={"triage-pill is-" + data.component.strength}
              >
                {data.component.strength}
              </span>
            </p>
            <p className="mt-1 text-sm text-muted">{reasons(data.component)}</p>
          </>
        ) : (
          <p className="text-sm text-muted">Nothing in the graph points to one area of the code.</p>
        )}
      </Step>

      <Step n={4} title="Found who knows it">
        {data.expert ? (
          <p>
            <a href={data.expert.url} target="_blank" rel="noreferrer" className="font-medium underline decoration-rule-strong underline-offset-4 hover:decoration-path">
              {data.expert.login}
            </a>
            <span className="text-muted">
              , {data.expert.authored_prs} merged pull requests authored and {data.expert.reviewed_prs} reviewed in this area
            </span>
          </p>
        ) : (
          <p className="text-sm text-muted">Nobody stands out for this area.</p>
        )}
      </Step>

      <Step n={5} title={applied ? "Wrote the reply" : "Drafted a reply"}>
        <figure className="reply-card">
          <CopyReply text={data.draft_reply} />
          <ReplyText text={data.draft_reply} />
        </figure>
        <p className="mt-2 text-xs text-muted">
          {data.model ? `Written by ${data.model} from these facts only.` : "Written from a template."} People are named by profile link,
          never @-mentioned.
        </p>
      </Step>

      <Step n={6} title={applied ? "Acted on the sandbox issue" : "What it would do on the sandbox"} last>
        <ul className="triage-action-list">
          {data.actions.map((action, i) => {
            const status = STATUS[action.status];
            const link = action.type === "comment" && action.detail?.startsWith("https://") ? action.detail : null;
            return (
              <li key={i} className="triage-action">
                <span className={"action-status is-" + action.status}>{status}</span>
                <span className="action-text">
                  <span>{ACTION_TEXT[action.type](action)}</span>
                  {link ? (
                    <a href={link} target="_blank" rel="noreferrer" className="action-link">View on GitHub ↗</a>
                  ) : (
                    action.detail && action.type !== "comment" && <span className="action-detail">{action.detail}</span>
                  )}
                </span>
              </li>
            );
          })}
        </ul>
      </Step>
    </ol>
  );
}
