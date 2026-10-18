import { expect, test } from "@playwright/test";

test.use({ colorScheme: "light", reducedMotion: "reduce" });

test("the header switch remembers the theme across sections and reloads", async ({ page }) => {
  await page.goto("/");
  const toggle = page.getByRole("switch", { name: "Dark mode" });
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  await expect(page.getByRole("button", { name: "About Aevion" })).toHaveCount(0);
  await toggle.focus();
  await page.keyboard.press("Space");
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("body")).toHaveCSS("background-color", "rgb(24, 26, 29)");
  await page.getByRole("link", { name: "Triage", exact: true }).click();
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  await page.reload();
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  await toggle.click();
  await page.reload();
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  await expect(page.locator("body")).toHaveCSS("background-color", "rgb(255, 255, 255)");
});

test("light is the default, even on a dark system, until the visitor chooses dark", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error" && /hydrat/i.test(message.text())) errors.push(message.text()); });
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  const toggle = page.getByRole("switch", { name: "Dark mode" });
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  await expect(page.locator("body")).toHaveCSS("background-color", "rgb(255, 255, 255)");
  await toggle.click();
  await page.reload();
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  await expect(page.locator('meta[name="theme-color"]')).toHaveAttribute("content", "#181a1d");
  expect(errors).toEqual([]);
});

test("switching themes keeps the selected source, evidence and camera intact", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Who knows the falkordb-py/ }).click();
  const source = page.getByRole("button", { name: "Source 1: gkorland", exact: true });
  await source.click();
  const camera = await page.locator(".react-flow__viewport").getAttribute("style");
  const nodes = await page.locator(".react-flow__node").evaluateAll(nodes => nodes.map(n => ({ id: n.getAttribute("data-id"), style: n.getAttribute("style") })));
  const edges = await page.locator(".react-flow__edge-path").evaluateAll(edges => edges.map(e => e.getAttribute("d")));
  await page.getByRole("switch", { name: "Dark mode" }).click();
  await expect(source).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("region", { name: "Selected node" })).toContainText("gkorland");
  await expect(page.locator(".react-flow")).toHaveClass(/dark/);
  expect(await page.locator(".react-flow__viewport").getAttribute("style")).toBe(camera);
  expect(await page.locator(".react-flow__node").evaluateAll(nodes => nodes.map(n => ({ id: n.getAttribute("data-id"), style: n.getAttribute("style") })))).toEqual(nodes);
  expect(await page.locator(".react-flow__edge-path").evaluateAll(edges => edges.map(e => e.getAttribute("d")))).toEqual(edges);
  await page.getByRole("tab", { name: /^Path/ }).click();
  await expect(page.getByRole("tabpanel")).toContainText("gkorland");
  await page.getByRole("tab", { name: /^Cypher/ }).click();
  await expect(page.getByRole("tabpanel").locator("pre").first()).toContainText("MATCH");
});

test("the theme still switches when browser storage is unavailable", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "localStorage", { get() { throw new DOMException("Storage blocked", "SecurityError"); } });
  });
  await page.goto("/");
  await page.getByRole("switch", { name: "Dark mode" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("link", { name: "Triage", exact: true }).click();
  await expect(page.getByRole("switch", { name: "Dark mode" })).toHaveAttribute("aria-checked", "true");
});
