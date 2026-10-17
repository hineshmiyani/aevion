import Link from "next/link";

const ORG = "FalkorDB";
const PAGES = [
  { href: "/", label: "Ask" },
  { href: "/triage", label: "Triage" },
] as const;

/** The masthead shared by every page: product, sections, and which org is loaded. */
export function SiteHeader({ current }: { current: (typeof PAGES)[number]["href"] }) {
  return (
    <header className="mb-10 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2 border-b border-rule pb-4">
      <div className="flex items-baseline gap-6">
        <p className="text-base font-semibold tracking-tight">Aevion</p>
        <nav aria-label="Sections">
          <ul className="flex gap-4 text-sm">
            {PAGES.map(({ href, label }) => (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={href === current ? "page" : undefined}
                  className={`inline-flex min-h-11 items-center underline-offset-4 ${
                    href === current ? "font-medium text-ink underline decoration-path decoration-2" : "text-muted hover:text-ink"
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
        <a href={`https://github.com/${ORG}`} className="text-ink underline decoration-rule-strong underline-offset-4 hover:decoration-path">
          {ORG} on GitHub
        </a>
        , 9 repositories, last 12 months
      </p>
    </header>
  );
}
