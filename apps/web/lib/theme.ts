export type Theme = "light" | "dark";
export const THEME_STORAGE_KEY = "aevion-theme";

// Runs before the page is painted, including when storage is blocked.
export const themeScript = `(() => {
  let theme;
  try { theme = localStorage.getItem("${THEME_STORAGE_KEY}"); } catch {}
  // Light unless the visitor chose dark; the system preference doesn't decide.
  if (theme !== "dark") theme = "light";
  document.documentElement.dataset.theme = theme;
})();`;
