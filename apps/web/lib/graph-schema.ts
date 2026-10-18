import { recordedAnswer } from "./recorded-answers";
import triageSample from "./triage-sample.json";
import type { EvidencePath, GraphStats } from "./types";

// The start-screen map: the graph model itself (README § Graph model), one node per label and
// one edge per relationship type, so a reader sees what Aevion can walk before asking.
// CachedAnswer and TriageRun are bookkeeping, self-loops (Issue REFERENCES Issue, Decision
// SUPERSEDES Decision) don't draw, and Issue ASSIGNED_TO Person would lie on top of Person
// AUTHORED Issue; they are left out.
const LABELS: [label: string, title: string, count?: keyof GraphStats][] = [
  ["Person", "People", "people"],
  ["PullRequest", "Pull requests", "pull_requests"],
  ["Issue", "Issues", "issues"],
  ["Comment", "Comments"],
  ["File", "Files"],
  ["Component", "Components", "components"],
  ["Decision", "Decisions", "decisions"],
  ["Repo", "Repositories", "repos"],
  ["Release", "Releases"],
  ["Label", "Labels"],
  ["Team", "Teams"],
];

// Pairs joined by more than one relationship type share one line, named by all of them.
const RELATIONSHIPS: [from: string, types: string, to: string][] = [
  ["Person", "AUTHORED|REVIEWED", "PullRequest"],
  ["Person", "AUTHORED", "Issue"],
  ["Person", "AUTHORED", "Comment"],
  ["Person", "OWNS", "Component"],
  ["Team", "OWNS", "Component"],
  ["Comment", "ON", "Issue"],
  ["Comment", "ON", "PullRequest"],
  ["PullRequest", "FIXES|REFERENCES", "Issue"],
  ["PullRequest", "MODIFIES", "File"],
  ["File", "IN_COMPONENT", "Component"],
  ["Issue", "HAS_LABEL", "Label"],
  ["PullRequest", "HAS_LABEL", "Label"],
  ["Component", "IN_REPO", "Repo"],
  ["Issue", "IN_REPO", "Repo"],
  ["PullRequest", "IN_REPO", "Repo"],
  ["Release", "IN_REPO", "Repo"],
  ["Release", "INCLUDES", "PullRequest"],
  ["Decision", "DECIDED_IN", "PullRequest"],
  ["Decision", "DECIDED_IN", "Issue"],
  ["Decision", "EVIDENCED_BY", "Comment"],
  ["Decision", "MADE_BY", "Person"],
  ["Decision", "AFFECTS", "Component"],
];

export const SCHEMA_PREFIX = "Schema:";
const idOf = (label: string) => SCHEMA_PREFIX + label;
export const SCHEMA_ANCHOR = idOf("PullRequest");

// Laid out by hand in three bands: what a change is filed under (top), the work itself (middle),
// and who does it, says it and decides it (bottom). Pull requests sit in the middle of it all.
export const SCHEMA_POSITIONS: Record<string, [number, number]> = Object.fromEntries(([
  ["Label", 100, 90], ["Repo", 400, 40], ["Release", 700, 90],
  ["Issue", 100, 290], ["PullRequest", 400, 290], ["File", 700, 290],
  ["Comment", 100, 490], ["Person", 400, 490], ["Component", 700, 490], ["Team", 940, 490],
  ["Decision", 250, 660],
] as const).map(([label, x, y]) => [idOf(label), [x, y]]));

export function graphSchema(stats?: GraphStats): EvidencePath {
  return {
    nodes: LABELS.map(([label, title, count]) => ({
      id: idOf(label), label,
      title: count && stats ? `${title} · ${Number(stats[count]).toLocaleString("en-US")}` : title,
    })),
    edges: RELATIONSHIPS.map(([from, type, to]) => ({ source: idOf(from), type, target: idOf(to) })),
  };
}

const count = (n: number) => n.toLocaleString("en-US");

/** The map's caption: the model stands for the whole graph; an answer is the slice it uses. */
export function mapCaption(evidence: EvidencePath, onSchema: boolean, stats: GraphStats | undefined, what: "answer" | "triage"): string | undefined {
  if (onSchema) return stats ? `This model covers ${count(stats.nodes)} nodes and ${count(stats.edges)} edges from ${count(stats.repos)} repositories.` : undefined;
  return `This ${what} uses ${count(evidence.nodes.length)} nodes and ${count(evidence.edges.length)} edges.`;
}

/** The labels a recorded answer's evidence uses, as schema nodes: the part of the model it walks. */
function walked(evidence: EvidencePath | undefined): string[] {
  return evidence ? [...new Set(evidence.nodes.map(n => idOf(n.label)))] : [];
}

export const questionWalk = (question: string) => walked(recordedAnswer(question)?.evidence);
// Every triage walks the same way (similar issue, its fix, the files and Component, the people),
// so the recorded run stands for all of them.
export const triageWalk = () => walked(triageSample.evidence as EvidencePath);
