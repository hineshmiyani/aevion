import { expect, test } from "@playwright/test";
import { graphSchema } from "../lib/graph-schema";

const SCHEMA_NODES = graphSchema().nodes.length;

test("source details have a readable panel beside the graph", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Who knows the falkordb-py/ }).click();
  await expect(page.locator(".react-flow__node")).toHaveCount(20);
  await page.getByRole("searchbox", { name: "Find a node" }).fill("gkorland");
  await page.getByRole("button", { name: "Find person: gkorland" }).click();
  const inspector = page.getByRole("region", { name: "Selected node" });
  expect((await inspector.boundingBox())!.width).toBeGreaterThanOrEqual(240);
  await expect(inspector.getByRole("link", { name: "Open on GitHub" })).toHaveAttribute("href", "https://github.com/gkorland");
  await page.getByRole("button", { name: "Fit all nodes" }).click();
  await expect.poll(() => page.locator(".network-canvas").evaluate(canvas => {
    const c = canvas.getBoundingClientRect();
    return [...canvas.querySelectorAll(".react-flow__node")].every(el => { const n = el.getBoundingClientRect(); return n.left >= c.left && n.right <= c.right && n.top >= c.top && n.bottom <= c.bottom; });
  })).toBe(true);
});

test("failed questions can retry and successful answers can be shared", async ({ page, context }) => {
  const { sampleAnswer } = await import("../lib/sample-answer");
  let calls = 0;
  await page.route("**/api/ask/stream", route => ++calls === 1
    ? route.fulfill({ status: 503, json: { error: "Please try again" } })
    : route.fulfill({ contentType: "text/event-stream", body: `data: ${JSON.stringify({ type: "answer", answer: sampleAnswer("test") })}\n\n` }));
  await page.goto("/");
  await page.getByRole("button", { name: /Who knows the falkordb-py/ }).click();
  await expect(page.locator(".workspace-sidebar").getByRole("alert")).toContainText("Please try again");
  await expect(page.locator(".react-flow__node")).toHaveCount(SCHEMA_NODES);
  await page.getByRole("button", { name: "Ask again", exact: true }).click();
  await expect(page.getByRole("button", { name: /^Source 1: / })).toBeVisible();
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.getByRole("button", { name: /^Share answer/ }).click();
  await expect(page.getByRole("button", { name: "Link copied" })).toBeVisible();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(page.url());
});

test("dark theme, left-side tabs, and source details remain accessible", async ({ page }) => {
  const { default: AxeBuilder } = await import("@axe-core/playwright");
  const scan = async () => {
    await page.waitForFunction(() => document.getAnimations().every(a => a.playState !== "running"));
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
    expect(results.violations.map(v => ({ rule: v.id, targets: v.nodes.map(n => n.target) }))).toEqual([]);
  };
  await page.goto("/");
  await expect(page.locator(".react-flow__node")).toHaveCount(SCHEMA_NODES);
  await page.getByRole("switch", { name: "Dark mode" }).click();
  await expect(page.getByRole("switch", { name: "Dark mode" })).toHaveAttribute("aria-checked", "true");
  await scan();
  await page.getByRole("button", { name: /Who knows the falkordb-py/ }).click();
  await page.getByRole("button", { name: "Source 1: gkorland", exact: true }).click();
  await expect(page.getByRole("region", { name: "Selected node" })).toBeVisible();
  await scan();
  await page.getByRole("button", { name: "Close node details" }).click();
  await page.getByRole("button", { name: "Graph options" }).click();
  await page.getByRole("checkbox", { name: "Edge labels" }).check();
  await scan();
  await page.getByRole("button", { name: "Graph options" }).click();
  await page.getByRole("tab", { name: /^Path/ }).click();
  await scan();
  await page.getByRole("tab", { name: /^Cypher/ }).click();
  await scan();
  await page.getByRole("tab", { name: /^Cypher/ }).press("Home");
  await expect(page.getByRole("tab", { name: "Answer", exact: true })).toBeFocused();
});

for (const [path, count] of [["/", SCHEMA_NODES], ["/triage", SCHEMA_NODES]] as const) {
  test(`the initial ${path} graph fits every node at desktop width`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(path);
    await expect(page.locator(".react-flow__node")).toHaveCount(count);
    await expect.poll(() => page.locator(".network-canvas").evaluate(canvas => {
      const c = canvas.getBoundingClientRect();
      return [...canvas.querySelectorAll(".react-flow__node")].every(el => { const n = el.getBoundingClientRect(); return n.left >= c.left && n.right <= c.right && n.top >= c.top && n.bottom <= c.bottom; });
    })).toBe(true);
  });
}

test("answer metadata distinguishes tool calls from Cypher queries", async ({ page }) => {
  const { sampleAnswer } = await import("../lib/sample-answer");
  const answer = { ...sampleAnswer("test"), sample: false };
  await page.route("**/api/ask/stream", route => route.fulfill({ contentType: "text/event-stream", body: `data: ${JSON.stringify({ type: "answer", answer })}\n\n` }));
  await page.goto("/");
  await page.getByRole("button", { name: /Who knows the falkordb-py/ }).click();
  await expect(page.locator(".answer-meta")).toContainText("1 tool call");
  await page.getByRole("tab", { name: /^Cypher/ }).click();
  await expect(page.getByRole("tabpanel").locator("pre")).toHaveCount(3);
});
