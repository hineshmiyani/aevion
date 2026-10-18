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
          <span className="cy-param">{part}</span>
          {name in params && <span className="cy-note">{` /* ${show(params[name])} */`}</span>}
        </Fragment>
      );
    }
    if (part.startsWith("'")) return <span key={i} className="cy-string">{part}</span>;
    if (new RegExp(`^${KEYWORDS.source}$`).test(part)) return <span key={i} className="cy-keyword">{part}</span>;
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
      className="cypher-copy"
      data-copied={copied || undefined}
      aria-label={copied ? "Copied" : "Copy"}
      title={copied ? "Copied" : "Copy query"}
    >
      {copied
        ? <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
        : <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V6a2 2 0 0 1 2-2h9" /></svg>}
      <span className="sr-only" aria-live="polite">{copied ? "Copied" : ""}</span>
    </button>
  );
}

export function CypherList({ cypher, calls = [], params = {} }: { cypher: string[]; calls?: ToolCall[]; params?: Record<string, unknown> }) {
  // A $name means the same thing in every query, so one value per name is enough.
  const values: Record<string, unknown> = { ...params };
  for (const call of calls) for (const [k, v] of Object.entries(call.args)) if (!(k in values)) values[k] = v;

  return (
    <div className="cypher">
      <p className="cypher-intro">The read-only queries that ran against FalkorDB, with the values they were given.</p>
      {calls.length > 0 && (
        <section aria-labelledby="cypher-calls">
          <h3 id="cypher-calls" className="cypher-heading">Tool calls</h3>
          <ol className="cypher-calls">
            {calls.map((call, i) => (
              <li key={i}>
                <code className="cypher-tool">{call.tool}</code>
                <span>{describe(call.tool, call.args)}</span>
              </li>
            ))}
          </ol>
        </section>
      )}
      <section aria-labelledby="cypher-queries">
        <h3 id="cypher-queries" className="cypher-heading">Queries</h3>
        {/* In the order each query first ran; a repeated query appears once, at its first run. */}
        <ol className="cypher-steps">
          {cypher.map((query, i) => (
            <li key={i} className="cypher-step">
              <figure className="cypher-block" aria-label={`Query ${i + 1} of ${cypher.length}`}>
                <CopyButton text={query} />
                <pre className="cypher-code">
                  <Highlighted query={query} params={values} />
                </pre>
              </figure>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
