"use client";

import { useState } from "react";

import { EvidenceGraph } from "@/components/ask/EvidenceGraph";
import { EvidenceTrail } from "@/components/ask/EvidenceTrail";
import type { ComponentPick, SimilarIssue, TriageAction, TriageResponse } from "@/lib/types";

import { InlineText, ReplyText } from "./ReplyText";

const STRENGTH_STYLE: Record<ComponentPick["strength"], string> = {
  strong: "border-ink text-ink",
  moderate: "border-rule-strong text-ink",
  weak: "border-dashed border-rule-strong text-muted",
};

const STATUS: Record<TriageAction["status"], { label: string; style: string }> = {
  proposed: { label: "Would do", style: "border-rule-strong text-ink" },
  done: { label: "Done", style: "border-ink bg-ink text-paper" },
  skipped: { label: "Skipped", style: "border-dashed border-rule-strong text-muted" },
  failed: { label: "Failed", style: "border-danger text-danger" },
};

const ACTION_TEXT: Record<TriageAction["type"], (a: TriageAction) => string> = {
  label: (a) => `Add the label “${a.value}”`,
  assign_or_mention: (a) => `Involve ${a.value}`,
  comment: () => "Post the reply",
};

function viaSummary(component: ComponentPick): string {
  const fixes = component.via.filter((v) => v.includes("#")).length;
  const reasons = [
    fixes && `${fixes} fix${fixes === 1 ? "" : "es"} for similar issues changed it`,
    component.via.some((v) => v.startsWith("name:")) && "its path matches the title",
    component.via.some((v) => v.includes("/") && !v.includes("#")) && "the issue names a file in it",
    component.via.some((v) => v.startsWith("the repo")) && component.via.find((v) => v.startsWith("the repo")),
  ].filter(Boolean);
  return reasons.join("; ");
}

function Similar({ issue }: { issue: SimilarIssue }) {
  return (
    <li className="py-2">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
        <a href={issue.url} target="_blank" rel="noreferrer" className="font-mono text-sm text-ink underline decoration-rule-strong underline-offset-2 hover:decoration-path">
          {issue.key}
        </a>
        <span className="text-xs text-muted">
          {issue.state.toLowerCase()}
          {issue.fixed_by.length > 0 && `, fixed by ${issue.fixed_by[0]}`}
        </span>
        {issue.likely_duplicate && (
          <span className="rounded-sm border border-path px-1.5 text-[11px] font-medium text-path">likely duplicate</span>
        )}
      </div>
      <p className="mt-0.5 text-sm leading-snug">
        <InlineText text={issue.title} />
      </p>
    </li>
  );
}

export function TriageResult({ data }: { data: TriageResponse }) {
  const [highlighted, setHighlighted] = useState<string | null>(null);
  const toggle = (id: string) => setHighlighted((current) => (current === id ? null : id));
  const similar = [...data.duplicates, ...data.related];
  const applied = data.mode === "apply";

  return (
    <div className="space-y-10">
      <div className="grid grid-cols-[minmax(0,1fr)] gap-x-12 gap-y-10 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <article aria-labelledby="triaged-issue" className="min-w-0 space-y-8">
          <header>
            <a href={data.issue.url} target="_blank" rel="noreferrer" className="font-mono text-sm text-muted underline decoration-rule-strong underline-offset-2 hover:decoration-path">
              {data.issue.key}
            </a>
            <h2 id="triaged-issue" className="mt-1 font-serif text-xl leading-snug">
              <InlineText text={data.issue.title} />
            </h2>
            {data.issue.context_repo && data.issue.context_repo !== data.issue.repo && (
              <p className="mt-2 text-sm text-muted">
                Triaged against <span className="font-mono text-ink">{data.issue.context_repo}</span>
                {data.issue.context_reason?.length ? `: ${data.issue.context_reason.join("; ")}` : ""}
              </p>
            )}
          </header>

          <section aria-labelledby="findings-heading">
            <h3 id="findings-heading" className="mb-3 text-sm font-medium">
              What the graph says
            </h3>
            <dl className="divide-y divide-rule border-y border-rule">
              <div className="grid gap-1 py-3 sm:grid-cols-[9rem_minmax(0,1fr)]">
                <dt className="text-sm text-muted">Area of the code</dt>
                <dd>
                  {data.component ? (
                    <>
                      <span className="font-mono text-sm">{data.component.name}</span>{" "}
                      <span className={`ml-1 rounded-sm border px-1.5 text-[11px] font-medium ${STRENGTH_STYLE[data.component.strength]}`}>
                        {data.component.strength}
                      </span>
                      <p className="mt-1 text-xs text-muted">{viaSummary(data.component)}</p>
                    </>
                  ) : (
                    <span className="text-sm text-muted">No clear area: nothing in the graph points to one.</span>
                  )}
                </dd>
              </div>
              <div className="grid gap-1 py-3 sm:grid-cols-[9rem_minmax(0,1fr)]">
                <dt className="text-sm text-muted">Who knows it</dt>
                <dd className="text-sm">
                  {data.expert ? (
                    <>
                      <a href={data.expert.url} target="_blank" rel="noreferrer" className="font-medium underline decoration-rule-strong underline-offset-2 hover:decoration-path">
                        {data.expert.login}
                      </a>
                      <span className="text-muted">
                        {" "}
                        · {data.expert.authored_prs} merged PRs authored, {data.expert.reviewed_prs} reviewed in this area
                      </span>
                    </>
                  ) : (
                    <span className="text-muted">Nobody stands out for this area.</span>
                  )}
                </dd>
              </div>
              <div className="grid gap-1 py-3 sm:grid-cols-[9rem_minmax(0,1fr)]">
                <dt className="text-sm text-muted">Similar issues</dt>
                <dd>
                  {similar.length ? (
                    <ul className="-my-2 divide-y divide-rule">
                      {similar.slice(0, 4).map((s) => (
                        <Similar key={s.key} issue={s} />
                      ))}
                    </ul>
                  ) : (
                    <span className="text-sm text-muted">None found.</span>
                  )}
                </dd>
              </div>
            </dl>
          </section>

          <section aria-labelledby="reply-heading">
            <h3 id="reply-heading" className="mb-3 text-sm font-medium">
              {applied ? "The reply Aevion posted" : "The reply Aevion would post"}
            </h3>
            <blockquote className="border-l-2 border-path pl-4">
              <ReplyText text={data.draft_reply} />
            </blockquote>
            <p className="mt-2 text-xs text-muted">
              {data.model ? `Drafted by ${data.model} from the facts above only.` : "Written from a template: no model was available."} It
              names people by profile link, never with an @-mention.
            </p>
          </section>

          <section aria-labelledby="actions-heading">
            <h3 id="actions-heading" className="mb-3 text-sm font-medium">
              {applied ? "What Aevion did" : "What Aevion would do on the sandbox"}
            </h3>
            <ol className="space-y-2">
              {data.actions.map((action, i) => {
                const status = STATUS[action.status];
                const link = action.type === "comment" && action.detail?.startsWith("https://") ? action.detail : null;
                return (
                  <li key={i} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm">
                    <span className={`inline-flex min-w-[4.75rem] justify-center rounded-sm border px-1.5 text-[11px] font-medium ${status.style}`}>
                      {status.label}
                    </span>
                    <span>{ACTION_TEXT[action.type](action)}</span>
                    {link ? (
                      <a href={link} target="_blank" rel="noreferrer" className="text-xs underline decoration-rule-strong underline-offset-2 hover:decoration-path">
                        View on GitHub
                      </a>
                    ) : (
                      action.detail && action.type !== "comment" && <span className="text-xs text-muted">{action.detail}</span>
                    )}
                  </li>
                );
              })}
            </ol>
          </section>

          {data.cypher.length > 0 && (
            <details className="border-t border-rule pt-3 text-sm text-muted">
              <summary className="select-none hover:text-ink">
                Show Cypher ({data.cypher.length} {data.cypher.length === 1 ? "query" : "queries"}, {data.evidence.edges.length} edges traced)
              </summary>
              {data.cypher.map((query, i) => (
                <pre key={i} className="mt-2 overflow-x-auto rounded-md border border-rule bg-surface p-3 font-mono text-[12px] leading-relaxed text-ink">
                  {query}
                </pre>
              ))}
            </details>
          )}

          {data.sample && (
            <p className="text-xs text-muted">
              This is a recorded sample dry run. Point the app at the Aevion API with AEVION_API_URL to triage live.
            </p>
          )}
        </article>

        <aside
          aria-labelledby="triage-trail-heading"
          className="lg:sticky lg:top-8 lg:max-h-[calc(100vh-4rem)] lg:self-start lg:overflow-y-auto lg:border-l lg:border-rule lg:pl-6"
        >
          <h2 id="triage-trail-heading" className="mb-3 text-sm font-medium">
            Where this comes from
          </h2>
          <EvidenceTrail evidence={data.evidence} citations={[]} highlighted={highlighted} />
        </aside>
      </div>

      {data.evidence.nodes.length > 1 && (
        <section aria-labelledby="triage-graph-heading">
          <h2 id="triage-graph-heading" className="mb-3 text-sm font-medium">
            The graph behind this triage
          </h2>
          <EvidenceGraph evidence={data.evidence} highlighted={highlighted} onSelect={toggle} />
        </section>
      )}
    </div>
  );
}
