// The five hero questions (SPEC US-1 to US-5), phrased with real FalkorDB names so the
// starter chips double as a tour of what Aevion can answer.
export const HERO_QUESTIONS = [
  { kind: "Who knows", question: "Who knows the falkordb-py client code best?" },
  { kind: "Why", question: "Why did FalkorDB gate main on a merge queue?" },
  { kind: "History", question: "What's been happening in GraphRAG-SDK's ingestion code lately?" },
  { kind: "Touches", question: "What else does FalkorDB/FalkorDB#3176 touch?" },
  { kind: "Catch up", question: "Catch me up on falkordb-browser since October 1." },
] as const;
