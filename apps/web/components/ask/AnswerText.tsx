"use client";

import { Fragment, useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

import { shortLabel } from "@/components/map/graph-layout";
import type { Citation, EvidenceNode } from "@/lib/types";
import { NodeGlyph, NODE_TYPE_NAMES } from "./NodeGlyph";

type AnswerTextProps = {
  text: string;
  citations: Citation[];
  nodes: Map<string, EvidenceNode>;
  onCite: (nodeId: string) => void;
  highlighted: string | null;
  /** The node under the pointer, here or on the map; its source pill lights up. */
  hovered?: string | null;
  onHover?: (nodeId: string | null) => void;
};

type Source = { n: number; id: string; node: EvidenceNode };
type Group = { key: number; sources: Source[]; trail: string };
type Card = { key: number; sources: Source[]; x: number; y: number; below: boolean };

// The agent writes plain text with **bold**, `code` and [n] citation markers. This small
// renderer can't inject HTML: everything becomes React text nodes.
// A marker keeps any punctuation right after it, so the two never wrap apart.
const TOKEN = /(\*\*[^*]+\*\*|`[^`]+`|\[\d+\][.,;:!?]?)/g;
const MARKER = /^\[(\d+)\]([.,;:!?]?)$/;
const CARD_WIDTH = 300;

// Decisions and comments have sentence-long titles; their type reads better than a truncated title.
const pillLabel = (node: EvidenceNode) =>
  node.label === "Decision" || node.label === "Comment" ? NODE_TYPE_NAMES[node.label] : shortLabel(node, 18) || (NODE_TYPE_NAMES[node.label] ?? node.label);
// The pill is named after the source a reader recognises fastest: a PR, issue, person or file.
const NAMED = ["PullRequest", "Issue", "Person", "Release", "File", "Component"];
const lead = (sources: Source[]) => sources.find((s) => NAMED.includes(s.node.label)) ?? sources[0];

export function AnswerText({ text, citations, nodes, onCite, highlighted, hovered = null, onHover }: AnswerTextProps) {
  const byNumber = new Map(citations.map((c) => [c.n, c.node_id]));
  const [card, setCard] = useState<Card | null>(null);
  const closing = useRef<ReturnType<typeof setTimeout> | null>(null);
  const opening = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reduced = useReducedMotion();
  const linked = hovered ?? highlighted;
  let pills = 0;

  const keep = () => {
    if (closing.current) clearTimeout(closing.current);
    if (opening.current) clearTimeout(opening.current);
    closing.current = opening.current = null;
  };
  // A short grace period lets the pointer travel from the pill into the card.
  const close = () => { keep(); closing.current = setTimeout(() => { setCard(null); onHover?.(null); }, 100); };
  useEffect(() => keep, []);

  // A brief hover intent keeps cards from flashing as the pointer crosses the text;
  // once one is open, moving to the next pill switches straight away.
  const open = (group: Group, target: HTMLElement, now = false) => {
    keep();
    const r = target.getBoundingClientRect();
    const x = Math.min(Math.max(r.left, 12), window.innerWidth - CARD_WIDTH - 12);
    const below = r.top < 90 + group.sources.length * 56;
    const show = () => { setCard({ key: group.key, sources: group.sources, x, y: below ? r.bottom + 6 : r.top - 6, below }); onHover?.(lead(group.sources).id); };
    if (now || card) show();
    else opening.current = setTimeout(show, 90);
  };

  const sourceOf = (part: string): { source: Source; trail: string } | null => {
    const marker = MARKER.exec(part);
    const n = marker ? Number(marker[1]) : 0;
    const id = marker ? byNumber.get(n) : undefined;
    const node = id ? nodes.get(id) : undefined;
    return marker && id && node ? { source: { n, id, node }, trail: marker[2] } : null;
  };

  const pill = (group: Group) => {
    const first = lead(group.sources);
    const rest = group.sources.filter((s) => s !== first);
    const ids = group.sources.map((s) => s.id);
    const lit = highlighted !== null && ids.includes(highlighted);
    const active = card?.key === group.key || (linked !== null && ids.includes(linked));
    const focus = (event: { currentTarget: HTMLElement }) => open(group, event.currentTarget.closest(".cite-pill") as HTMLElement, true);
    return (
      <span key={"cite-" + group.key} className="whitespace-nowrap">
        <span className={`cite-pill ${lit ? "is-lit" : ""} ${active ? "is-active" : ""}`}
          onMouseEnter={(e) => open(group, e.currentTarget)} onMouseLeave={close}>
          <button type="button" className="cite-pill-main" onClick={() => onCite(first.id)} onFocus={focus} onBlur={close}
            aria-label={`Source ${first.n}: ${first.node.title}`} aria-pressed={highlighted === first.id}>
            {pillLabel(first.node)}{rest.length > 0 && <span className="cite-pill-more" aria-hidden="true">+{rest.length}</span>}
          </button>
          {/* The pill shows one name; each further source stays reachable by keyboard and screen reader. */}
          {rest.map((s) => <button key={s.n} type="button" className="sr-only" onClick={() => onCite(s.id)} onFocus={focus} onBlur={close}
            aria-label={`Source ${s.n}: ${s.node.title}`} aria-pressed={highlighted === s.id} />)}
        </span>
        {group.trail}
      </span>
    );
  };

  const renderInline = (line: string): ReactNode[] => {
    const parts = line.split(TOKEN).filter(Boolean);
    const out: ReactNode[] = [];
    let group: Group | null = null;
    const flush = () => { if (group) out.push(pill(group)); group = null; };
    parts.forEach((part, i) => {
      const cited = sourceOf(part);
      if (cited) {
        group ??= { key: pills++, sources: [], trail: "" };
        group.sources.push(cited.source);
        if (cited.trail) { group.trail = cited.trail; flush(); }
        return;
      }
      // "[1] [2]" reads as one group: drop the space between adjacent markers.
      if (group && /^\s+$/.test(part) && parts[i + 1] && sourceOf(parts[i + 1])) return;
      flush();
      if (part.startsWith("**") && part.endsWith("**")) out.push(<strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>);
      else if (part.startsWith("`") && part.endsWith("`")) out.push(<code key={i} className="bg-surface px-1 py-0.5 font-mono text-[0.8em]">{part.slice(1, -1)}</code>);
      else out.push(<Fragment key={i}>{part}</Fragment>);
    });
    flush();
    return out;
  };

  return (
    <div className="max-w-[68ch] space-y-4 font-serif text-answer leading-[1.7] text-ink">
      {text.split(/\n{2,}/).map((block, i) => {
        const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
        const items = lines.filter((line) => /^[-*] /.test(line));
        // A block of "- " lines is a list; a lead-in line before the items stays a paragraph.
        if (items.length > 0 && items.length >= lines.length - 1) {
          const lead = lines[0] && !/^[-*] /.test(lines[0]) ? lines[0] : null;
          return (
            <div key={i}>
              {lead && <p>{renderInline(lead)}</p>}
              <ul className="mt-2 list-disc space-y-1.5 pl-5 marker:text-muted">
                {items.map((item, j) => (
                  <li key={j}>{renderInline(item.slice(2))}</li>
                ))}
              </ul>
            </div>
          );
        }
        return <p key={i}>{renderInline(lines.join(" "))}</p>;
      })}
      {typeof document !== "undefined" && createPortal(
        <AnimatePresence>
          {card && (
            <motion.div key="cite-card" className="cite-card-anchor" aria-hidden="true"
              initial={{ opacity: 0, scale: reduced ? 1 : 0.97, x: card.x, y: card.y + (reduced ? 0 : card.below ? -4 : 4) }}
              animate={{ opacity: 1, scale: 1, x: card.x, y: card.y }}
              exit={{ opacity: 0, scale: reduced ? 1 : 0.97, transition: { duration: reduced ? 0 : 0.12, ease: [0.4, 0, 1, 1] } }}
              transition={reduced ? { duration: 0 } : { opacity: { duration: 0.16 }, scale: { duration: 0.2, ease: [0.2, 0.7, 0.2, 1] }, default: { type: "spring", stiffness: 520, damping: 42 } }}>
              <div className="cite-card" data-below={card.below || undefined} style={{ width: CARD_WIDTH }} onMouseEnter={keep} onMouseLeave={close}>
                <motion.div key={card.key} initial={{ opacity: reduced ? 1 : 0 }} animate={{ opacity: 1 }} transition={{ duration: reduced ? 0 : 0.14 }}>
                  {card.sources.map((s) => (
                    <button key={s.n} type="button" tabIndex={-1} className={`cite-card-row ${highlighted === s.id ? "is-lit" : ""}`}
                      onMouseEnter={() => onHover?.(s.id)} onClick={() => onCite(s.id)}>
                      <NodeGlyph label={s.node.label} />
                      <span className="cite-card-text">
                        <span className="cite-card-meta">{NODE_TYPE_NAMES[s.node.label] ?? s.node.label}</span>
                        <span className="cite-card-title">{s.node.title}</span>
                      </span>
                    </button>
                  ))}
                </motion.div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>,
        document.body,
      )}
    </div>
  );
}
