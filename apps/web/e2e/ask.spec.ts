import { expect, test } from "@playwright/test";

import { HERO_QUESTIONS } from "../lib/hero-questions";

const starter = (i: number) => new RegExp(HERO_QUESTIONS[i].question.replace("?", "\\?"));

test("the first screen says what Aevion is and shows the graph working", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Ask how FalkorDB works." })).toBeVisible();
  await expect(page.getByText(/nodes and .* edges from \d+ repositories/)).toBeVisible();
  // A real answer's evidence is already on the map, with the route drawn through its sources.
  await expect(page.getByRole("group", { name: /Evidence map for a recent answer/ })).toBeVisible();
  await expect(page.locator(".route-leg").first()).toBeAttached();
  await expect(page.getByRole("button", { name: "Read the answer" })).toBeVisible();
});

test("a starter question shows its steps, a cited answer, and sources that light up the map", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: starter(0) }).click();

  await expect(page.getByRole("list", { name: "What Aevion did" })).toContainText("Found this answer already in the graph");
  const firstSource = page.getByRole("button", { name: /^Source 1: / });
  await expect(firstSource).toBeVisible();
  const title = (await firstSource.getAttribute("aria-label"))!.replace(/^Source 1: /, "");

  // The citation and the map node name the same evidence node.
  await firstSource.click();
  await expect(firstSource).toHaveAttribute("aria-pressed", "true");
  const mapNode = page.getByRole("button", { name: new RegExp(`: ${title}$`) }).and(page.locator("g"));
  await expect(mapNode).toHaveAttribute("aria-pressed", "true");

  // Selecting on the map by keyboard clears the citation again.
  await mapNode.focus();
  await page.keyboard.press("Enter");
  await expect(firstSource).toHaveAttribute("aria-pressed", "false");

  // The Cypher is one tab away, and the tabs work with arrow keys.
  const mapTab = page.getByRole("tab", { name: "Map" });
  await mapTab.focus();
  await page.keyboard.press("ArrowLeft");
  await expect(page.getByRole("tab", { name: /^Cypher/ })).toHaveAttribute("aria-selected", "true");
  await expect(page.locator("pre").first()).toContainText("MATCH");
  await expect(page.getByText(/recorded sample answer|Answered/)).toBeVisible();
});

test("the page never scrolls sideways", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: starter(0) }).click();
  await expect(page.getByRole("button", { name: /^Source 1: / })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("with reduced motion, the route is drawn at once", async ({ browser }) => {
  const context = await browser.newContext({ reducedMotion: "reduce" });
  const page = await context.newPage();
  await page.goto("/");
  const leg = page.locator(".route-leg").first();
  await expect(leg).toBeAttached();
  await page.waitForTimeout(100);
  const offset = await leg.evaluate((el) => getComputedStyle(el).strokeDashoffset);
  expect(parseFloat(offset)).toBe(0);
  await context.close();
});

test("a ?q= link asks that question, and each answer can be shared", async ({ page }) => {
  const question = HERO_QUESTIONS[0].question;
  await page.goto(`/?q=${encodeURIComponent(question)}`);
  await expect(page.getByRole("heading", { level: 2, name: question })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Source 1: / })).toBeVisible();
  expect(new URL(page.url()).searchParams.get("q")).toBe(question);
  await expect(page.getByRole("button", { name: "Copy link to this answer" })).toBeVisible();
});

test("pressing / jumps to the question box", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: "Map" }).focus();
  await page.keyboard.press("/");
  await expect(page.getByRole("textbox", { name: "Your question" })).toBeFocused();
  await expect(page.getByRole("textbox", { name: "Your question" })).toHaveValue("");
});

test("the Cypher tab names the tools and fills in the parameters", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: /^Cypher/ }).click();
  const panel = page.getByRole("tabpanel");
  await expect(panel.getByText("experts_for", { exact: true })).toBeVisible();
  await expect(panel.locator("pre").first()).toContainText(/\$component \/\* '.+' \*\//);
  // Highlighting must not change the text: every keyword appears once.
  for (const pre of await panel.locator("pre").all()) await expect(pre).not.toContainText(/\b(MATCH|CALL|WITH|RETURN|WHERE)\1/);
  await expect(panel.getByRole("button", { name: "Copy" }).first()).toBeVisible();
});

test("on a phone the map comes before the starter questions", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile", "phone layout only");
  await page.goto("/");
  const map = await page.getByRole("group", { name: /Evidence map for a recent answer/ }).boundingBox();
  const starters = await page.getByRole("heading", { name: "Try a question" }).boundingBox();
  expect(map!.y).toBeLessThan(starters!.y);
});
