// Server-only reads for the first screen: live graph stats and one real, cached answer, so
// the map is already working when the page loads. Falls back to recorded data when no API
// is configured (local UI work, previews, Playwright). Import from server components only.

import { apiBase } from "./proxy";
import { recordedAnswer } from "./recorded-answers";
import { HERO_QUESTIONS } from "./hero-questions";
import type { AskResponse, GraphStats } from "./types";

const ORG = "FalkorDB";
export const FEATURED_QUESTION = HERO_QUESTIONS[1].question; // the merge-queue decision

// Recorded from the production graph on 2026-10-18, shown only without an API.
const SAMPLE_STATS: GraphStats = {
  org: ORG, nodes: 20961, edges: 80642, repos: 9, people: 390, pull_requests: 3544,
  issues: 2326, decisions: 534, components: 325, sample: true,
};

export async function getStats(): Promise<GraphStats> {
  const api = apiBase();
  if (!api) return SAMPLE_STATS;
  try {
    const response = await fetch(`${api}/api/stats?org=${ORG}`, { next: { revalidate: 60 }, signal: AbortSignal.timeout(4000) });
    return response.ok ? ((await response.json()) as GraphStats) : SAMPLE_STATS;
  } catch {
    return SAMPLE_STATS;
  }
}

/** A cached hero answer: free, instant, and not counted toward anyone's rate limit. */
export async function getFeatured(): Promise<{ question: string; data: AskResponse }> {
  const api = apiBase();
  const recorded = recordedAnswer(HERO_QUESTIONS[0].question);
  if (!recorded) throw new Error("Missing the recorded featured answer");
  const fallback = { question: HERO_QUESTIONS[0].question, data: recorded };
  if (!api) return fallback;
  try {
    const response = await fetch(`${api}/api/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ org: ORG, question: FEATURED_QUESTION }),
      next: { revalidate: 300 },
      signal: AbortSignal.timeout(6000),
    });
    if (!response.ok) return fallback;
    const data = (await response.json()) as AskResponse;
    return data.cached ? { question: FEATURED_QUESTION, data } : fallback;
  } catch {
    return fallback;
  }
}
