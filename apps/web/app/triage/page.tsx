import type { Metadata } from "next";

import { SiteHeader } from "@/components/SiteHeader";
import { TriageExperience } from "@/components/triage/TriageExperience";
import { getStats } from "@/lib/server-api";

export const metadata: Metadata = {
  title: "Triage · Aevion",
  description: "Triage a GitHub issue with the FalkorDB knowledge graph: similar issues, the area of the code, and who knows it.",
};

export default async function TriagePage() {
  const stats = await getStats();
  return (
    <div className="app-frame">
      <a
        href="#main"
        className="sr-only bg-ink px-3 py-2 text-sm text-paper focus:not-sr-only focus:absolute focus:top-3 focus:left-3"
      >
        Skip to triage
      </a>
      <SiteHeader current="/triage" />
      <main id="main" className="flex-1">
        <TriageExperience org="FalkorDB" stats={stats} />
      </main>
    </div>
  );
}
