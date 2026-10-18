import Link from "next/link";

import { ThemeToggle } from "./ThemeToggle";
const PAGES = [
  { href: "/", label: "Ask" },
  { href: "/triage", label: "Triage" },
] as const;

/** Three stops joined by a route: the evidence path, which is what Aevion draws. */
export function RouteMark({ size = 22 }: { size?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden className="shrink-0">
      <polyline points="4,17 10,8 20,13" fill="none" stroke="var(--path)" strokeWidth="2.5" strokeLinecap="square" />
      <rect x="1.5" y="14.5" width="5" height="5" fill="var(--ink)" />
      <rect x="7.5" y="5.5" width="5" height="5" fill="var(--ink)" />
      <rect x="17.5" y="10.5" width="5" height="5" fill="var(--ink)" />
    </svg>
  );
}

/** The masthead shared by every page. */
export function SiteHeader({ current }: { current: (typeof PAGES)[number]["href"] }) {
  return (
    <header className="app-header">
      <div className="flex items-center gap-7">
        <Link href="/" className="flex items-center gap-2 text-lg font-semibold tracking-tight text-ink">
          <RouteMark />
          Aevion
        </Link>
        <nav aria-label="Sections">
          <ul className="section-nav">
            {PAGES.map(({ href, label }) => (
              <li key={href}>
                <Link href={href} aria-current={href === current ? "page" : undefined}>
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
      <div className="flex items-center gap-5">
        <p className="header-source">
          Reading the <a href="https://github.com/FalkorDB" target="_blank" rel="noreferrer">FalkorDB organisation on GitHub</a>, last 12 months
        </p>
        <ThemeToggle />
      </div>
    </header>
  );
}
