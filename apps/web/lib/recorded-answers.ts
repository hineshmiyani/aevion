import saved from "./recorded-hero-answers.json";
import type { AskResponse } from "./types";

const answers = saved.answers as { question: string; answer: AskResponse }[];
const normalize = (question: string) => question.trim().replace(/\s+/g, " ").toLowerCase();

export const OFFLINE_QUESTION_MESSAGE = "This local demo includes the five suggested questions. Choose one to see its saved production answer.";

/** Complete cached responses copied from production; no model or network calls. */
export function recordedAnswer(question: string): AskResponse | null {
  const entry = answers.find(item => normalize(item.question) === normalize(question));
  return entry ? { ...entry.answer, sample: true } : null;
}
