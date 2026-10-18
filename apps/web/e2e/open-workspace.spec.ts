import { expect, test } from "@playwright/test";

test("all five starters are plain visible rows in a wider question panel", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Ask about FalkorDB." })).toBeVisible();
  await expect(page.locator(".question-suggestions > li")).toHaveCount(5);
  await expect(page.locator("details")).toHaveCount(0);
  expect((await page.locator(".workspace-sidebar").boundingBox())!.width).toBeGreaterThan(440);
});

test("full answer and left-side evidence tabs share a persistent graph", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.getByRole("button", { name: /Who knows the falkordb-py/ }).click();
  await expect(page.getByRole("button", { name: /^Source 7: / })).toBeVisible();
  await expect(page.getByRole("list", { name: "What Aevion did" })).toBeVisible();
  await expect(page.locator("details")).toHaveCount(0);
  const graph = await page.locator(".network-canvas").elementHandle();
  const position = await page.locator(".react-flow__viewport").getAttribute("style");
  await page.getByRole("tab", { name: /^Path/ }).click();
  await expect(page.locator(".workspace-sidebar").getByRole("button", { name: "Show gkorland on map" })).toBeVisible();
  await page.getByRole("tab", { name: /^Cypher/ }).click();
  await expect(page.locator(".workspace-sidebar pre").first()).toContainText("MATCH");
  expect(await graph!.evaluate(el => el.isConnected)).toBe(true);
  await expect(page.locator(".react-flow__viewport")).toHaveAttribute("style", position!);
  await page.getByRole("button", { name: "Back to questions" }).click();
  await expect(page.getByRole("textbox", { name: "Your question" })).toBeFocused();
  await expect(page.getByRole("button", { name: /Back to answer|Ask another question/ })).toHaveCount(0);
});

test("back cancels a pending question and allows a fresh question", async ({ page }) => {
  const { sampleAnswer } = await import("../lib/sample-answer");
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  let calls = 0;
  await page.route("**/api/ask/stream", async route => {
    if (++calls === 1) await held;
    await route.fulfill({ contentType: "text/event-stream", body: `data: ${JSON.stringify({ type: "answer", answer: sampleAnswer("test") })}\n\n` }).catch(() => {});
  });
  await page.goto("/");
  await page.getByRole("textbox", { name: "Your question" }).fill("First question");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("heading", { name: "First question", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Back to questions" }).click();
  await page.getByRole("textbox", { name: "Your question" }).fill("Second question");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  release();
  await expect(page.getByRole("button", { name: /^Source 7: / })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Second question", exact: true })).toBeVisible();
  expect(new URL(page.url()).searchParams.get("q")).toBe("Second question");
});

test("triage shows its complete timeline and a single sandbox link without folds", async ({ page }) => {
  await page.goto("/triage");
  await expect(page.getByRole("link", { name: /Open a new issue on the sandbox/ })).toHaveCount(1);
  await expect(page.locator("details")).toHaveCount(0);
  await page.getByRole("button", { name: /FalkorDB\/FalkorDB#3357/ }).click();
  const steps = page.getByRole("list", { name: "How Aevion triaged this issue" });
  await expect(steps.locator(":scope > li")).toHaveCount(6);
  await expect(page.getByText("Proposed", { exact: true })).toHaveCount(3);
  await expect(page.locator("details")).toHaveCount(0);
  await expect(page.getByRole("tab", { name: "Answer", exact: true })).toHaveAttribute("aria-selected", "true");
  await page.getByRole("button", { name: "Back to issues" }).click();
  await expect(page.getByRole("textbox", { name: "Issue", exact: true })).toBeFocused();
});
