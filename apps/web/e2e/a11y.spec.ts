import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { graphSchema } from "../lib/graph-schema";

const SCHEMA_NODES = graphSchema().nodes.length;

// WCAG 2.2 AA, scanned with axe on each view in both themes, with real content on screen.
async function scan(page: Page) {
  // Scan the settled page: mid-fade text would be measured at partial opacity.
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running"));
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  const summary = results.violations.map((v) => `${v.id}: ${v.nodes.length} × ${v.help}`);
  expect(summary, JSON.stringify(results.violations.map(v => ({ rule: v.id, nodes: v.nodes.map(n => ({ target: n.target, reason: n.failureSummary })) })), null, 2)).toEqual([]);
}

// Both themes must retain readable content and usable controls.
for (const colorScheme of ["light", "dark"] as const) {
  test.describe(`system theme ${colorScheme}`, () => {
    test.use({ colorScheme });

    test("the page follows the system preference", async ({ page }) => {
      await page.goto("/");
      const background = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
      expect(background).toBe(colorScheme === "light" ? "rgb(255, 255, 255)" : "rgb(24, 26, 29)");
    });

    test("the first screen", async ({ page }) => {
      await page.goto("/");
      await expect(page.locator(".react-flow__node")).toHaveCount(SCHEMA_NODES);
      await scan(page);
    });

    test("an answer", async ({ page }) => {
      await page.goto("/");
      await page.getByRole("button", { name: /falkordb-py client/ }).click();
      await expect(page.getByRole("button", { name: /^Source 1: / })).toBeVisible();
      await scan(page);
    });

    test("a triage", async ({ page }) => {
      await page.goto("/triage");
      await page.getByRole("button", { name: /FalkorDB\/FalkorDB#3357/ }).click();
      await expect(page.getByRole("heading", { name: "Found who knows it" })).toBeVisible();
      await scan(page);
    });
  });
}
