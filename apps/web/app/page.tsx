import { AskExperience } from "@/components/ask/AskExperience";
import { SiteHeader } from "@/components/SiteHeader";
import { getFeatured, getStats } from "@/lib/server-api";

const ORG = "FalkorDB";

export default async function Home() {
  const [featured, stats] = await Promise.all([getFeatured(), getStats()]);
  return (
    <div className="app-frame">
      <a
        href="#main"
        className="sr-only bg-ink px-3 py-2 text-sm text-paper focus:not-sr-only focus:absolute focus:top-3 focus:left-3"
      >
        Skip to the question
      </a>
      <SiteHeader current="/" />
      <main id="main" className="flex-1">
        <AskExperience org={ORG} featured={featured} stats={stats} />
      </main>
    </div>
  );
}
