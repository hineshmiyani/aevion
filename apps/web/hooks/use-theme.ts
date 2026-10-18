"use client";

import { useSyncExternalStore } from "react";
import { THEME_STORAGE_KEY, type Theme } from "@/lib/theme";

const THEME_EVENT = "aevion-theme-change";
let preference: Theme | null | undefined;

function storedPreference(): Theme | null {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    return stored === "light" || stored === "dark" ? stored : null;
  } catch { return null; }
}

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  // Colour transitions would let each control fade on its own clock; flip the palette in one frame.
  if (root.dataset.theme !== theme) {
    root.dataset.themeSwitching = "";
    requestAnimationFrame(() => requestAnimationFrame(() => delete root.dataset.themeSwitching));
  }
  root.dataset.theme = theme;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#181a1d" : "#ffffff");
  window.dispatchEvent(new Event(THEME_EVENT));
}

function subscribe(onChange: () => void) {
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  if (preference === undefined) preference = storedPreference();
  const sync = () => applyTheme(preference ?? (media.matches ? "dark" : "light"));
  const onStorage = (event: StorageEvent) => {
    if (event.key !== THEME_STORAGE_KEY && event.key !== null) return;
    preference = storedPreference();
    sync();
  };
  window.addEventListener(THEME_EVENT, onChange);
  window.addEventListener("storage", onStorage);
  media.addEventListener("change", sync);
  sync();
  return () => {
    window.removeEventListener(THEME_EVENT, onChange);
    window.removeEventListener("storage", onStorage);
    media.removeEventListener("change", sync);
  };
}

const getSnapshot = (): Theme => document.documentElement.dataset.theme === "dark" ? "dark" : "light";
const getServerSnapshot = (): Theme => "light";

export function setTheme(theme: Theme) {
  preference = theme;
  try { localStorage.setItem(THEME_STORAGE_KEY, theme); } catch { /* Keep the choice for this visit. */ }
  applyTheme(theme);
}

export function useTheme() {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
