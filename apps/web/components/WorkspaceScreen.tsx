"use client";

import { AnimatePresence, motion, useIsPresent, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

type Screen = "start" | "answer";

function Panel({ screen, children }: { screen: Screen; children: ReactNode }) {
  const present = useIsPresent();
  const reduced = useReducedMotion();
  return <motion.div className="workspace-screen" data-screen={screen}
    inert={!present} aria-hidden={!present || undefined}
    initial={{ opacity: reduced ? 1 : 0, x: reduced ? 0 : screen === "answer" ? 16 : -16 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: reduced ? 0 : screen === "answer" ? 12 : -12, transition: { duration: reduced ? 0 : 0.12, ease: [0.4, 0, 1, 1] } }}
    transition={{ duration: reduced ? 0 : 0.3, ease: [0.2, 0.7, 0.2, 1] }}>
    {children}
  </motion.div>;
}

/** `startFocus` names the field that takes focus on the way back to the start screen. It waits
 * for the outgoing screen to leave, because the start screen only mounts after that. */
export function WorkspaceScreen({ screen, startFocus, children }: { screen: Screen; startFocus?: string; children: ReactNode }) {
  // AnimatePresence calls the latest render's callback, so `screen` is already the new one.
  const settle = () => {
    if (screen === "start" && startFocus) requestAnimationFrame(() => document.querySelector<HTMLElement>(startFocus)?.focus());
  };
  return <AnimatePresence initial={false} mode="wait" onExitComplete={settle}><Panel key={screen} screen={screen}>{children}</Panel></AnimatePresence>;
}
