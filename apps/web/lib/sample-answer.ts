// A compact fixture for isolated UI tests. The app serves full saved production answers
// from recorded-answers.ts when AEVION_API_URL is not configured.
// It is assembled from a real experts_for result recorded from the FalkorDB graph, so the
// sample shows genuine names, PRs and evidence edges rather than invented data.
import experts from "./experts-sample.json";
import type { AskResponse, Citation, ToolResult } from "./types";

const result = experts as unknown as ToolResult;

type ExpertRow = {
  login: string;
  score: number;
  authored_prs: number;
  reviewed_prs: number;
  comments: number;
  evidence: { pr: string; title: string; role: string }[];
};

export function sampleAnswer(question: string): AskResponse {
  void question; // accepted for API parity; the sample always shows the same expert answer
  const rows = result.rows as unknown as ExpertRow[];
  const citations: Citation[] = [];
  const cite = (nodeId: string) => {
    const existing = citations.find((c) => c.node_id === nodeId);
    if (existing) return `[${existing.n}]`;
    const n = citations.length + 1;
    citations.push({ n, node_id: nodeId });
    return `[${n}]`;
  };

  const component = String(result.args.component);
  const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;
  const lines = rows.map((row, i) => {
    // Cite in reading order: the person first, then their PRs.
    const person = `**${row.login}**${cite(`Person:${row.login}`)}`;
    const lead = i === 0 ? `${person} knows it best` : person;
    const prs = row.evidence
      .slice(0, 2)
      .map((e) => `${e.role === "AUTHORED" ? "authored" : "reviewed"} “${e.title}”${cite(`PullRequest:${e.pr}`)}`)
      .join(" and ");
    return `${lead}: ${plural(row.authored_prs, "merged PR")} authored, ${row.reviewed_prs} reviewed, ${plural(row.comments, "comment")}. Recently ${prs}.`;
  });

  return {
    answer: [
      `For the \`${component}\` component of FalkorDB/falkordb-py, ranked by recent merged-PR work:`,
      ...lines,
      "Scores weight authorship over reviews and fade with age, so recent work counts most.",
    ].join("\n\n"),
    citations,
    tool_calls: [{ tool: "experts_for", args: result.args }],
    evidence: result.evidence,
    cypher: result.cypher,
    model: "sample",
    cached: true,
    sample: true,
  };
}
