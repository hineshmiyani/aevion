import type { ReactNode } from "react";

import type { ComponentPick, SimilarIssue, TriageAction, TriageResponse } from "@/lib/types";

import { InlineText, ReplyText } from "./ReplyText";

/*
 * The triage as the agent's steps, in the order it took them. The spine is a route: each
 * marker turns amber as its step arrives. The steps are the real results of one request,
 * revealed in sequence once it returns (the triage API doesn't stream).
 */

const STRENGTH: Record<ComponentPick["strength"], { label: string; style: string }> = {
  strong: { label: "strong", style: "border-ink text-ink" },
  moderate: { label: "moderate", style: "border-rule-strong text-ink" },
  weak: { label: "weak, a guess", style: "border-dashed border-rule-strong text-muted" },
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
        <a href={issue.url} target="_blank" rel="noreferrer" className="font-mono text-[13px] text-ink underline decoration-rule-strong underline-offset-2 hover:decoration-path">
          {issue.key}
        </a>
        <span className="text-xs text-muted">
          {issue.state.toLowerCase()}
          {issue.fixed_by.length > 0 && `, fixed by ${issue.fixed_by[0]}`}
        </span>
        {issue.likely_duplicate && <span className=" border border-path px-1.5 text-[11px] font-medium text-path">likely duplicate</span>}
      </div>
      <p className="mt-0.5 text-[15px] leading-snug">
        <InlineText text={issue.title} />
      </p>
    </li>
  );
}

function Step({ n, title, children, last = false }: { n: number; title: string; children: ReactNode; last?: boolean }) {
  return (
    <li className="arrive relative grid grid-cols-[2rem_minmax(0,1fr)] gap-x-3" style={{ animationDelay: `${(n - 1) * 140}ms` }}>
      {!last && <span aria-hidden className="absolute top-8 bottom-0 left-[15px] w-[3px] bg-path/70" />}
      <span aria-hidden className="relative z-10 flex size-8 items-center justify-center border-2 border-path bg-surface text-sm font-semibold text-path tabular-nums">
        {n}
      </span>
      <div className={`min-w-0 ${last ? "" : "pb-7"}`}>
        <h3 className="pt-1 font-medium">{title}</h3>
        <div className="mt-2">{children}</div>
      </div>
    </li>
  );
}

export function TriageSteps({ data }: { data: TriageResponse }) {
  const similar = [...data.duplicates, ...data.related];
  const applied = data.mode === "apply";
  const context = data.issue.context_repo && data.issue.context_repo !== data.issue.repo ? data.issue.context_repo : null;

  return (
    <ol aria-label="How Aevion triaged this issue" className="mt-2">
      <Step n={1} title="Read the issue">
        <a href={data.issue.url} target="_blank" rel="noreferrer" className="font-mono text-[13px] text-muted underline decoration-rule-strong underline-offset-2 hover:decoration-path">
          {data.issue.key}
        </a>
        <p className="mt-1 font-serif text-xl leading-snug">
          <InlineText text={data.issue.title} />
        </p>
        {context && (
          <p className="mt-1.5 text-sm text-muted">
            Read as an issue about <span className="font-mono text-[13px] text-ink">{context}</span>
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
              <span className="font-mono text-[15px]">{data.component.name}</span>{" "}
              <span className={`ml-1 border px-1.5 text-xs font-medium ${STRENGTH[data.component.strength].style}`}>
                {STRENGTH[data.component.strength].label}
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
        <blockquote className="border-l-[3px] border-path pl-4">
          <ReplyText text={data.draft_reply} />
        </blockquote>
        <p className="mt-2 text-xs text-muted">
          {data.model ? `Written by ${data.model} from these facts only.` : "Written from a template."} People are named by profile link,
          never @-mentioned.
        </p>
      </Step>

      <Step n={6} title={applied ? "Acted on the sandbox issue" : "What it would do on the sandbox"} last>
        <ul className="space-y-2">
          {data.actions.map((action, i) => {
            const status = STATUS[action.status];
            const link = action.type === "comment" && action.detail?.startsWith("https://") ? action.detail : null;
            return (
              <li key={i} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-[15px]">
                <span className={`inline-flex min-w-[4.75rem] justify-center border px-1.5 text-xs font-medium ${status.style}`}>{status.label}</span>
                <span>{ACTION_TEXT[action.type](action)}</span>
                {link ? (
                  <a href={link} target="_blank" rel="noreferrer" className="text-sm text-path underline underline-offset-2">
                    View on GitHub
                  </a>
                ) : (
                  action.detail && action.type !== "comment" && <span className="text-sm text-muted">{action.detail}</span>
                )}
              </li>
            );
          })}
        </ul>
      </Step>
    </ol>
  );
}
