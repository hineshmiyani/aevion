import Link from "next/link";

const ORG = "FalkorDB";
const PAGES = [
  { href: "/", label: "Ask" },
  { href: "/triage", label: "Triage" },
] as const;

/** Three stops joined by a route: the evidence path, which is what Aevion draws. */
function RouteMark() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden className="shrink-0">
      <polyline points="4,17 10,8 20,13" fill="none" stroke="var(--path)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="4" cy="17" r="2.6" fill="var(--ink)" />
      <circle cx="10" cy="8" r="2.6" fill="var(--ink)" />
      <circle cx="20" cy="13" r="2.6" fill="var(--ink)" />
    </svg>
  );
}

/** The masthead shared by every page: product, sections, and which org is loaded. */
export function SiteHeader({ current }: { current: (typeof PAGES)[number]["href"] }) {
  return (
    <header className="mb-10 flex flex-wrap items-center justify-between gap-x-6 gap-y-2 lg:mb-12">
      <div className="flex items-center gap-7">
        <Link href="/" className="flex items-center gap-2 text-lg font-semibold tracking-tight text-ink">
          <RouteMark />
          Aevion
        </Link>
        <nav aria-label="Sections">
          <ul className="flex gap-1 text-[15px]">
            {PAGES.map(({ href, label }) => (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={href === current ? "page" : undefined}
                  className={`inline-flex min-h-11 items-center rounded-md px-3 transition-colors ${
                    href === current ? "bg-surface font-medium text-ink shadow-[inset_0_0_0_1px_var(--rule)]" : "text-muted hover:text-ink"
                  }`}
                >
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
      <p className="text-sm text-muted">
        Reading the{" "}
        <a href={`https://github.com/${ORG}`} className="text-ink underline decoration-rule-strong underline-offset-4 hover:decoration-path">
          {ORG} organisation on GitHub
        </a>
        , last 12 months
      </p>
    </header>
  );
}
