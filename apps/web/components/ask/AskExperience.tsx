"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { EvidencePanel } from "@/components/map/EvidencePanel";
import { WorkspaceScreen } from "@/components/WorkspaceScreen";
import { WorkspaceViews, type WorkspaceView } from "@/components/WorkspaceViews";
import { BackIcon, CheckIcon, LinkIcon, SendIcon } from "@/components/WorkspaceIcons";
import { useAskStream } from "@/hooks/use-ask-stream";
import { graphSchema, questionWalk, SCHEMA_ANCHOR, SCHEMA_POSITIONS } from "@/lib/graph-schema";
import type { AskResponse, Citation, EvidencePath, GraphStats } from "@/lib/types";
import { AnswerResult } from "./AnswerResult";
import { QuestionSuggestions } from "./QuestionSuggestions";
import { AnswerPlaceholder, ErrorState } from "./AnswerStates";
import { ProgressLog } from "./ProgressLog";

type Props = { org: string; featured: { question: string; data: AskResponse }; stats?: GraphStats };

export function AskExperience({ org, featured, stats }: Props) {
  const { state, ask, reset } = useAskStream(org);
  const [question, setQuestion] = useState("");
  const box = useRef<HTMLTextAreaElement>(null);
  const [highlighted, setHighlighted] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [previous, setPrevious] = useState(featured.data);
  const [view, setView] = useState<WorkspaceView>("answer");
  const busy = state.status === "working";
  const idle = state.status === "idle";
  const shown = state.status === "success" ? state.data : previous;
  const nodes = useMemo(() => new Map(shown.evidence.nodes.map(n => [n.id, n])), [shown]);
  // The start screen maps the graph model; a starter lights the part of it its answer walks.
  // While an answer loads, the map keeps whatever it last showed.
  const [starter, setStarter] = useState<string | null>(null);
  const schema = useMemo(() => ({ evidence: graphSchema(stats), citations: [] as Citation[] }), [stats]);
  const [mapBefore, setMapBefore] = useState<{ evidence: EvidencePath; citations: Citation[] }>(schema);
  const map = idle ? schema : state.status === "success" ? state.data : mapBefore;
  const onSchema = map.evidence === schema.evidence;
  const lit = useMemo(() => idle && starter ? questionWalk(starter) : [], [idle, starter]);
  const toggle = (id: string) => setHighlighted(current => current === id ? null : id);
  const submit = (text: string) => {
    const trimmed = text.trim();
    if (busy) return;
    if (!trimmed) { box.current?.focus(); return; }
    setPrevious(shown);
    setMapBefore({ evidence: map.evidence, citations: map.citations });
    setStarter(null);
    setHighlighted(null);
    setView("answer");
    setQuestion("");
    void ask(trimmed);
  };
  const onSubmit = (event: FormEvent) => { event.preventDefault(); submit(question); };
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); submit(question); }
  };
  const goBack = useCallback(() => {
    setPrevious(shown);
    reset();
    setHighlighted(null);
    setHovered(null);
    setView("answer");
    setQuestion("");
    const url = new URL(window.location.href);
    url.searchParams.delete("q");
    window.history.replaceState(null, "", url);
    // Already on the start screen (the "/" shortcut), nothing transitions, so focus now.
    requestAnimationFrame(() => box.current?.focus());
  }, [reset, shown]);
  const opened = useRef(false);
  useEffect(() => {
    if (opened.current) return;
    opened.current = true;
    const q = new URLSearchParams(window.location.search).get("q")?.trim();
    // The initial URL is an external source of the question.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (q) submit(q.slice(0, 500));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- read the entry URL once
  }, []);
  const asked = state.status === "idle" ? null : state.question;
  useEffect(() => {
    if (asked === null) return;
    const url = new URL(window.location.href);
    url.searchParams.set("q", asked);
    window.history.replaceState(null, "", url);
  }, [asked]);
  useEffect(() => {
    const onSlash = (event: globalThis.KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (event.key !== "/" || target.closest("input, textarea, select, [contenteditable='true']") || event.metaKey || event.ctrlKey || event.altKey) return;
      event.preventDefault();
      goBack();
    };
    window.addEventListener("keydown", onSlash);
    return () => window.removeEventListener("keydown", onSlash);
  }, [goBack]);
  const [linkCopied, setLinkCopied] = useState(false);
  const copyLink = async () => {
    try { await navigator.clipboard.writeText(window.location.href); setLinkCopied(true); setTimeout(() => setLinkCopied(false), 1500); }
    catch { setLinkCopied(false); }
  };

  return <div className="evidence-workspace" data-view={idle ? "start" : "answer"}>
    <aside className={"workspace-sidebar " + (idle ? "is-start" : "")}>
      <WorkspaceScreen screen={idle ? "start" : "answer"} startFocus="#question">{idle ? <div className="question-entry">
        <h1>Ask about FalkorDB.</h1>
        <form onSubmit={onSubmit} className="question-form">
          <label htmlFor="question" className="sr-only">Your question</label>
          <textarea id="question" ref={box} rows={3} value={question} onChange={e => setQuestion(e.target.value)} onKeyDown={onKeyDown} maxLength={500} placeholder="Ask about people, code, or decisions…" aria-describedby="question-hint" />
          <div className="question-form-footer">
            <span className="question-form-hint" aria-hidden="true"><kbd>Enter</kbd> to ask · <kbd>Shift</kbd> + <kbd>Enter</kbd> for a new line</span>
            <button type="submit" className="send-button" data-empty={question.trim() ? undefined : ""} aria-label="Ask" title="Ask (Enter)"><SendIcon /></button>
          </div>
          <span id="question-hint" className="sr-only">Enter to ask, Shift+Enter for a new line. Press / to return here.</span>
        </form>
        <QuestionSuggestions busy={busy} onAsk={submit} onPreview={setStarter} />
      </div> : <>
        <header className="answer-header">
          <button type="button" className="ghost-button back-button" aria-label="Back to questions" title="Back to questions" onClick={goBack}><BackIcon /></button>
          <h1 className="answer-title">{state.question}</h1>
        </header>
        <WorkspaceViews actions={state.status === "success" && <>
          <button type="button" className="ghost-button copy-link" data-copied={linkCopied || undefined} aria-label={linkCopied ? "Link copied" : "Share answer, copies its link"} onClick={copyLink}>
            {linkCopied ? <CheckIcon /> : <LinkIcon />}<span aria-hidden="true">{linkCopied ? "Link copied" : "Share answer"}</span>
          </button>
          <span className="sr-only" aria-live="polite">{linkCopied ? "Link copied" : ""}</span>
        </>} view={view} onView={setView} evidence={shown.evidence} citations={shown.citations} cypher={shown.cypher} calls={shown.tool_calls} highlighted={highlighted} onSelect={id => setHighlighted(id)} onHover={setHovered}>
          <article aria-live="polite" aria-busy={busy}>
            {busy && <><div className="answer-progress"><ProgressLog steps={state.steps} working /></div><AnswerPlaceholder /></>}
            {state.status === "success" && <AnswerResult data={state.data} nodes={nodes} highlighted={highlighted} hovered={hovered} onHover={setHovered} onCite={toggle} steps={state.steps} />}
            {state.status === "error" && <><ErrorState message={state.error} retryAfterSeconds={state.retryAfterSeconds} onRetry={() => ask(state.question)} /><div className="answer-progress is-after"><ProgressLog steps={state.steps} working={false} /></div></>}
          </article>
        </WorkspaceViews>
      </>}</WorkspaceScreen>
    </aside>
    <div className="workspace-map"><EvidencePanel preview={idle} revision={state.status === "success" ? state.question : idle ? "schema" : "pending"} busy={busy} evidence={map.evidence} citations={map.citations} anchor={onSchema ? SCHEMA_ANCHOR : undefined} labelled={onSchema} positions={onSchema ? SCHEMA_POSITIONS : undefined} lit={lit} highlighted={highlighted} hovered={idle ? null : hovered} onHover={setHovered} onSelect={toggle} label={onSchema ? "Graph model" : busy ? "Evidence map from the previous answer while loading" : state.status === "error" ? "Evidence map from the previous answer" : "Evidence map for this answer"} /></div>
  </div>;
}
