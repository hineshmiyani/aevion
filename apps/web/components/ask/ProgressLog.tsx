import type { Step } from "@/hooks/use-ask-stream";

// What each tool is doing, in words a reader would use.
export function describe(tool: string, args: Record<string, unknown>): string {
  const a = (k: string) => (typeof args[k] === "string" ? (args[k] as string) : "");
  switch (tool) {
    case "experts_for":
      return `Finding who knows ${a("component") || "this area"}`;
    case "decision_trail":
      return a("topic") ? `Searching decisions about “${a("topic")}”` : `Searching decisions in ${a("component")}`;
    case "area_history":
      return `Reading the history of ${a("component")}`;
    case "related_work":
      return `Following links from ${a("key")}`;
    case "catch_up":
      return `Catching up on ${a("repo") || a("component")}${a("since") ? ` since ${a("since")}` : ""}`;
    case "triage_candidates":
      return `Triaging ${a("issue")}`;
    default:
      return `Running ${tool}`;
  }
}

/**
 * The agent's real steps, as they happen: each tool call, then the writing. The model "writes"
 * between tool rounds too, but only the last stretch, after every query, is the answer, so
 * earlier ones aren't listed. A query that returned nothing says so instead of looking like a hit.
 */
export function ProgressLog({ steps, working }: { steps: Step[]; working: boolean }) {
  const lastTool = steps.findLastIndex((s) => s.kind === "tool");
  const visible = steps.filter((s, i) => s.kind !== "writing" || i > lastTool);
  const shown: Step[] = visible.length === 0 && working ? [{ kind: "writing", done: false }] : visible;
  return (
    <ol aria-label="What Aevion did" className="space-y-1.5 text-sm">
      {shown.map((step, i) => {
        const done = step.kind === "cached" || step.done;
        const empty = step.kind === "tool" && step.done && step.rows === 0;
        const text =
          step.kind === "cached"
            ? "Found this answer already in the graph"
            : step.kind === "writing"
              ? steps.length === 0
                ? "Reading the question"
                : "Writing the answer from what the graph returned"
              : describe(step.tool, step.args);
        const marker = empty ? "border border-rule-strong" : done ? "bg-path" : "working bg-muted";
        return (
          <li key={i} className="arrive flex flex-wrap items-baseline gap-x-2.5">
            <span aria-hidden className={`inline-block size-2 shrink-0 translate-y-[-1px] ${marker}`} />
            <span className={done && !empty ? "text-ink" : "text-muted"}>{text}</span>
            {step.kind === "tool" && step.done && (
              <span className="text-muted tabular-nums">
                {empty ? `found nothing, ${step.ms} ms` : `${step.rows} ${step.rows === 1 ? "node" : "nodes"} in ${step.ms} ms`}
              </span>
            )}
            <span className="sr-only">{done ? "done" : "in progress"}</span>
          </li>
        );
      })}
    </ol>
  );
}
