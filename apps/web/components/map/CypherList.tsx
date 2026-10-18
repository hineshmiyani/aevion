"use client";

import { Fragment, useState } from "react";

import { describe } from "@/components/ask/ProgressLog";
import type { ToolCall } from "@/lib/types";

/*
 * The Cypher behind an answer, readable: which tools ran (and with what), then each query with
 * its $parameters filled in where a tool argument of the same name says what they were.
 * The API sends the queries as one de-duplicated list, so a query isn't tied to one tool call.
 */

const KEYWORDS =
  /\b(?:OPTIONAL MATCH|MATCH|WHERE|RETURN|WITH|UNWIND|CALL|YIELD|ORDER BY|LIMIT|SKIP|AS|AND|OR|NOT|IN|IS NULL|IS NOT NULL|DISTINCT|CASE|WHEN|THEN|ELSE|END|DESC|ASC|CONTAINS|STARTS WITH|ENDS WITH)\b/;
const TOKEN = new RegExp(`(${KEYWORDS.source}|\\$[A-Za-z_]\\w*|'[^']*')`, "g");

function show(value: unknown): string {
  return typeof value === "string" ? `'${value}'` : JSON.stringify(value);
}

/** Splits a query into keyword, parameter, string and plain runs, so each can be styled. */
function Highlighted({ query, params }: { query: string; params: Record<string, unknown> }) {
  return query.split(TOKEN).map((part, i) => {
    if (!part) return null;
    if (part.startsWith("$")) {
      const name = part.slice(1);
      return (
        <Fragment key={i}>
          <span className="text-path">{part}</span>
          {name in params && <span className="text-muted">{` /* ${show(params[name])} */`}</span>}
        </Fragment>
      );
    }
    if (part.startsWith("'")) return <span key={i} className="text-muted">{part}</span>;
    if (new RegExp(`^${KEYWORDS.source}$`).test(part)) return <span key={i} className="font-semibold">{part}</span>;
    return <Fragment key={i}>{part}</Fragment>;
  });
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={() => {
        void navigator.clipboard?.writeText(text).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        });
      }}
      className="min-h-11 px-2 text-xs font-medium text-muted underline decoration-rule-strong underline-offset-2 hover:text-ink"
    >
      <span aria-live="polite">{copied ? "Copied" : "Copy"}</span>
    </button>
  );
}

export function CypherList({ cypher, calls = [], params = {} }: { cypher: string[]; calls?: ToolCall[]; params?: Record<string, unknown> }) {
  // A $name means the same thing in every query, so one value per name is enough.
  const values: Record<string, unknown> = { ...params };
  for (const call of calls) for (const [k, v] of Object.entries(call.args)) if (!(k in values)) values[k] = v;

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">The read-only queries that ran against FalkorDB, with the values they were given.</p>
      {calls.length > 0 && (
        <ol className="space-y-1 border-l-[3px] border-path pl-3 text-sm">
          {calls.map((call, i) => (
            <li key={i}>
              <span className="font-mono text-[13px] text-ink">{call.tool}</span>
              <span className="text-muted">: {describe(call.tool, call.args)}</span>
            </li>
          ))}
        </ol>
      )}
      {cypher.map((query, i) => (
        <figure key={i} className="m-0 border border-rule bg-surface">
          <figcaption className="flex items-center justify-between border-b border-rule pl-3 text-xs text-muted">
            Query {i + 1} of {cypher.length}
            <CopyButton text={query} />
          </figcaption>
          <pre className="p-3 font-mono text-[12px] leading-relaxed whitespace-pre-wrap text-ink">
            <Highlighted query={query} params={values} />
          </pre>
        </figure>
      ))}
    </div>
  );
}
