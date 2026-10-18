import type { CSSProperties } from "react";
import { ArrowIcon } from "@/components/WorkspaceIcons";
import { HERO_QUESTIONS } from "@/lib/hero-questions";

/** `onPreview` names the starter being pointed at, so the map can light where it lands. */
export function QuestionSuggestions({ onAsk, busy, onPreview }: { onAsk: (question: string) => void; busy: boolean; onPreview?: (question: string | null) => void }) {
  return <div className="suggestions"><h2>Try a question</h2><ul className="question-suggestions">
    {HERO_QUESTIONS.map(({ question, kind }, i) => <li key={question} style={{ "--i": i } as CSSProperties}><button type="button" disabled={busy} onClick={() => onAsk(question)}
      onMouseEnter={() => onPreview?.(question)} onMouseLeave={() => onPreview?.(null)} onFocus={() => onPreview?.(question)} onBlur={() => onPreview?.(null)}><span className="question-kind">{kind}</span><span className="question-label">{question}</span><span className="question-chevron"><ArrowIcon /></span></button></li>)}
  </ul></div>;
}
