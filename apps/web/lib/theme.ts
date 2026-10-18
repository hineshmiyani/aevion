export type Theme = "light" | "dark";
export const THEME_STORAGE_KEY = "aevion-theme";

// Runs before the page is painted, including when storage is blocked.
export const themeScript = `(() => {
  let theme;
  try { theme = localStorage.getItem("${THEME_STORAGE_KEY}"); } catch {}
  if (theme !== "light" && theme !== "dark") {
    theme = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  document.documentElement.dataset.theme = theme;
})();`;
