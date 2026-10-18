"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { setTheme, useTheme } from "@/hooks/use-theme";

function SunIcon() {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
    <circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4m0-14.2-1.4 1.4M6.3 17.7l-1.4 1.4" />
  </svg>;
}

function MoonIcon() {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M20.5 14a8.5 8.5 0 0 1-10.5-10.5A8.5 8.5 0 1 0 20.5 14Z" />
  </svg>;
}

/** One button: shows the current theme and flips it. Still a switch named "Dark mode" for assistive tech. */
export function ThemeToggle() {
  const dark = useTheme() === "dark";
  const reduced = useReducedMotion();
  const swap = reduced ? {} : { initial: { opacity: 0, rotate: -60, scale: 0.6 }, animate: { opacity: 1, rotate: 0, scale: 1 }, exit: { opacity: 0, rotate: 60, scale: 0.6 } };
  return (
    <button type="button" role="switch" aria-label="Dark mode" aria-checked={dark}
      title={dark ? "Switch to light mode" : "Switch to dark mode"}
      className="theme-toggle" onClick={() => setTheme(dark ? "light" : "dark")}>
      <span className="theme-toggle-icon">
        <AnimatePresence initial={false} mode="popLayout">
          <motion.span key={dark ? "moon" : "sun"} {...swap} transition={{ duration: 0.22, ease: [0.2, 0.7, 0.2, 1] }}>
            {dark ? <MoonIcon /> : <SunIcon />}
          </motion.span>
        </AnimatePresence>
      </span>
      <span className="theme-toggle-label" aria-hidden="true">{dark ? "Dark" : "Light"}</span>
    </button>
  );
}
