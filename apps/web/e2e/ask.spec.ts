import { expect, test } from "@playwright/test";

import { HERO_QUESTIONS } from "../lib/hero-questions";

test("a starter question yields a cited answer whose sources light up the graph", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: new RegExp(HERO_QUESTIONS[0].question.replace("?", "\\?")) }).click();

  const firstSource = page.getByRole("button", { name: /^Source 1: / });
  await expect(firstSource).toBeVisible();
  const title = (await firstSource.getAttribute("aria-label"))!.replace(/^Source 1: /, "");

  // The citation, the trail row and the graph node all name the same evidence node.
  await firstSource.click();
  await expect(firstSource).toHaveAttribute("aria-pressed", "true");
  const graphNode = page.getByRole("button", { name: new RegExp(`: ${title}$`) }).and(page.locator("g"));
  await expect(graphNode).toHaveAttribute("aria-pressed", "true");

  // Selecting from the graph by keyboard clears the citation again.
  await graphNode.focus();
  await page.keyboard.press("Enter");
  await expect(firstSource).toHaveAttribute("aria-pressed", "false");

  // The Cypher behind the answer is one click away.
  await page.getByText(/How this was answered/).click();
  await page.getByText(/Show Cypher \(\d+ quer/).click();
  await expect(page.locator("pre").first()).toContainText("MATCH");
});

test("the page never scrolls sideways", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: new RegExp(HERO_QUESTIONS[0].question.replace("?", "\\?")) }).click();
  await expect(page.getByRole("button", { name: /^Source 1: / })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
