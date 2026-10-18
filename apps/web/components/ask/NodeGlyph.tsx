// One shape per node type, so the evidence trail never relies on colour alone.

export const NODE_SHAPES: Record<string, React.ReactNode> = {
  Person: <circle cx="7" cy="7" r="5.25" />,
  PullRequest: <rect x="2" y="2" width="10" height="10" />,
  Issue: <rect x="3.1" y="3.1" width="7.8" height="7.8" transform="rotate(45 7 7)" />,
  Component: <polygon points="7,1.5 11.8,4.25 11.8,9.75 7,12.5 2.2,9.75 2.2,4.25" />,
  File: <rect x="2" y="5" width="10" height="4" />,
  Decision: <polygon points="7,1.5 12.5,12 1.5,12" />,
  Comment: <path d="M2 3h10v6H6l-3 2.5V9H2z" />,
  Release: <path d="M3 1.5v11M3 2h8l-2 2.5 2 2.5H3" />,
};

export const NODE_TYPE_NAMES: Record<string, string> = {
  Person: "person",
  PullRequest: "pull request",
  Issue: "issue",
  Component: "component",
  File: "file",
  Decision: "decision",
  Comment: "comment",
  Release: "release",
};

export function NodeGlyph({ label, className = "" }: { label: string; className?: string }) {
  const outlineOnly = label === "Release";
  return (
    <svg
      viewBox="0 0 14 14"
      width="14"
      height="14"
      aria-hidden
      className={`shrink-0 ${className}`}
      style={{ color: `var(--node-${label.toLowerCase()}, var(--muted))` }}
      fill={outlineOnly ? "none" : "currentColor"}
      stroke="currentColor"
      strokeWidth={outlineOnly ? 1.6 : 0}
    >
      {NODE_SHAPES[label] ?? <circle cx="7" cy="7" r="4" />}
    </svg>
  );
}
