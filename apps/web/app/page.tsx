import { AskExperience } from "@/components/ask/AskExperience";

const ORG = "FalkorDB";

export default function Home() {
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-4 py-6 sm:px-8 lg:py-10">
      <a
        href="#main"
        className="sr-only rounded-sm bg-ink px-3 py-2 text-sm text-paper focus:not-sr-only focus:absolute focus:top-3 focus:left-3"
      >
        Skip to the question
      </a>
      <header className="mb-10 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-b border-rule pb-4">
        <p className="text-base font-semibold tracking-tight">Aevion</p>
        <p className="text-sm text-muted">
          <a href={`https://github.com/${ORG}`} className="text-ink underline decoration-rule-strong underline-offset-4 hover:decoration-path">
            {ORG} on GitHub
          </a>
          , 9 repositories, last 12 months
        </p>
      </header>
      <main id="main" className="flex-1">
        <AskExperience org={ORG} />
      </main>
    </div>
  );
}
