import { expect, test } from "@playwright/test";

import { HERO_QUESTIONS } from "../lib/hero-questions";
import { graphSchema } from "../lib/graph-schema";

const SCHEMA_NODES = graphSchema().nodes.length;

const starter = (i: number) => new RegExp(HERO_QUESTIONS[i].question.replace("?", "\\?"));

test("the first screen shows the question entry and graph", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Ask about FalkorDB." })).toBeVisible();
  await expect(page.getByRole("switch", { name: "Dark mode" })).toBeVisible();
  // The graph model is already on the map: what Aevion can walk, before anything is asked.
  await expect(page.getByRole("group", { name: /Graph model/ })).toBeVisible();
  await expect(page.locator(".react-flow__node")).toHaveCount(SCHEMA_NODES);
  await expect(page.locator(".question-suggestions > li")).toHaveCount(5);
  await expect(page.locator("details")).toHaveCount(0);
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
  const mapNode = page.getByRole("button", { name: new RegExp(`: ${title}$`) }).and(page.locator(".react-flow__node"));
  await expect(mapNode).toHaveAttribute("aria-pressed", "true");

  // Selecting on the map by keyboard clears the citation again.
  await mapNode.focus();
  await page.keyboard.press("Enter");
  await expect(firstSource).toHaveAttribute("aria-pressed", "false");

  // The Cypher is one tab away, and the tabs work with arrow keys.
  await page.getByRole("tab", { name: "Answer", exact: true }).focus();
  await page.keyboard.press("ArrowLeft");
  await expect(page.getByRole("tab", { name: /^Cypher/ })).toHaveAttribute("aria-selected", "true");
  await expect(page.locator("pre").first()).toContainText("MATCH");
  await page.keyboard.press("ArrowRight");
  await expect(page.locator(".answer-meta")).toContainText("Saved production answer");
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
  await page.getByRole("button", { name: starter(0) }).click();
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
  await expect(page.getByRole("heading", { level: 1, name: question })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Source 1: / })).toBeVisible();
  expect(new URL(page.url()).searchParams.get("q")).toBe(question);
  await expect(page.getByRole("button", { name: /^Share answer/ })).toBeVisible();
});

test("pressing / jumps to the question box", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".react-flow__node")).toHaveCount(SCHEMA_NODES);
  await page.getByRole("switch", { name: "Dark mode" }).focus();
  await page.keyboard.press("/");
  await expect(page.getByRole("textbox", { name: "Your question" })).toBeFocused();
  await expect(page.getByRole("textbox", { name: "Your question" })).toHaveValue("");
});

test("the Cypher tab names the tools and fills in the parameters", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: starter(0) }).click();
  await page.getByRole("tab", { name: /^Cypher/ }).click();
  const panel = page.getByRole("tabpanel");
  await expect(panel.getByText("experts_for", { exact: true })).toHaveCount(2);
  await expect(panel.locator("pre").first()).toContainText(/\$component \/\* '.+' \*\//);
  // Highlighting must not change the text: every keyword appears once.
  for (const pre of await panel.locator("pre").all()) await expect(pre).not.toContainText(/\b(MATCH|CALL|WITH|RETURN|WHERE)\1/);
  await expect(panel.getByRole("button", { name: "Copy" }).first()).toBeVisible();
});

test("on a phone the map comes before the starter questions", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile", "phone layout only");
  await page.goto("/");
  const map = await page.getByRole("group", { name: /Graph model/ }).boundingBox();
  const starters = await page.getByRole("heading", { name: "Try a question" }).boundingBox();
  expect(map!.y).toBeLessThan(starters!.y);
});

test("the detail card never covers the node it describes", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "mobile", "the phone card spans the width; checked on desktop");
  await page.goto("/");
  const map = page.getByRole("group", { name: /Graph model/ });
  await expect(map.locator(".react-flow__node")).toHaveCount(SCHEMA_NODES);
  const nodes = await map.locator(".react-flow__node").all();
  for (const node of nodes.slice(0, 10)) {
    await page.getByRole("button", { name: "Fit all nodes" }).click();
    await expect.poll(async () => {
      const [n, c] = [await node.boundingBox(), await map.boundingBox()];
      return n!.x >= c!.x && n!.y >= c!.y && n!.x + n!.width <= c!.x + c!.width && n!.y + n!.height <= c!.y + c!.height;
    }).toBe(true);
    await node.click();
    const card = page.getByRole("region", { name: "Selected node" });
    await expect.poll(async () => {
      const [a, c] = [await node.boundingBox(), await card.boundingBox()];
      return !(a!.x + a!.width < c!.x || a!.x > c!.x + c!.width || a!.y + a!.height < c!.y || a!.y > c!.y + c!.height);
    }, { message: "The node remains clear of the inspector after the camera settles" }).toBe(false);
    await page.getByRole("button", { name: "Close node details" }).click();
  }
});
