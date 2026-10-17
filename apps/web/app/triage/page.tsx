import type { Metadata } from "next";

import { SiteHeader } from "@/components/SiteHeader";
import { TriageExperience } from "@/components/triage/TriageExperience";

export const metadata: Metadata = {
  title: "Triage · Aevion",
  description: "Triage a GitHub issue with the FalkorDB knowledge graph: similar issues, the area of the code, and who knows it.",
};

export default function TriagePage() {
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-4 py-6 sm:px-8 lg:py-10">
      <a
        href="#main"
        className="sr-only rounded-sm bg-ink px-3 py-2 text-sm text-paper focus:not-sr-only focus:absolute focus:top-3 focus:left-3"
      >
        Skip to triage
      </a>
      <SiteHeader current="/triage" />
      <main id="main" className="flex-1">
        <TriageExperience org="FalkorDB" />
      </main>
    </div>
  );
}
