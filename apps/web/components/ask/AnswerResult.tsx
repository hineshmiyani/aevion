import type { AskResponse, EvidenceNode } from "@/lib/types";
import type { Step } from "@/hooks/use-ask-stream";
import { AnswerText } from "./AnswerText";
import { ProgressLog } from "./ProgressLog";

export function AnswerResult({ data, nodes, highlighted, hovered, onHover, onCite, steps }: { data: AskResponse; nodes: Map<string, EvidenceNode>; highlighted: string | null; hovered: string | null; onHover: (id: string | null) => void; onCite: (id: string) => void; steps: Step[] }) {
  return <div className="answer-result arrive">
    <div className="answer-progress"><ProgressLog steps={steps} working={false} /></div>
    <AnswerText text={data.answer} citations={data.citations} nodes={nodes} highlighted={highlighted} hovered={hovered} onHover={onHover} onCite={onCite} />
    <p className="answer-meta">{data.sample ? (data.model === "sample" ? "A recorded sample answer. Live questions are off in this local demo." : "Saved production answer. Live questions are off in this local demo.") : [data.cached ? "Cached answer" : "Graph answer", data.model, data.elapsed_ms == null ? null : String(data.elapsed_ms) + " ms", String(data.tool_calls.length) + " tool call" + (data.tool_calls.length === 1 ? "" : "s"), String(data.evidence.edges.length) + " connections"].filter(Boolean).join(" · ")}</p>
  </div>;
}
