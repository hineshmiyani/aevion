import { AskExperience } from "@/components/ask/AskExperience";
import { SiteHeader } from "@/components/SiteHeader";
import { getFeatured, getStats } from "@/lib/server-api";

const ORG = "FalkorDB";

export default async function Home() {
  const [stats, featured] = await Promise.all([getStats(), getFeatured()]);
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 py-6 sm:px-8 lg:py-8">
      <a
        href="#main"
        className="sr-only bg-ink px-3 py-2 text-sm text-paper focus:not-sr-only focus:absolute focus:top-3 focus:left-3"
      >
        Skip to the question
      </a>
      <SiteHeader current="/" />
      <main id="main" className="flex-1">
        <AskExperience org={ORG} stats={stats} featured={featured} />
      </main>
    </div>
  );
}
