import { expect, test } from "@playwright/test";
import saved from "../lib/recorded-hero-answers.json";
import { graphSchema } from "../lib/graph-schema";

test("both local endpoints return the exact saved production answer for each starter", async ({ request }) => {
  for (const { question, answer } of saved.answers) {
    const data = { org: "FalkorDB", question };
    const response = await request.post("/api/ask", { data });
    expect(response.ok()).toBe(true);
    expect(await response.json()).toEqual({ ...answer, sample: true });
    const stream = await request.post("/api/ask/stream", { data });
    expect(stream.ok()).toBe(true);
    const events = (await stream.text()).split("\n\n").filter(Boolean).map(chunk => JSON.parse(chunk.slice(6)));
    expect(events.find(event => event.type === "answer").answer).toEqual({ ...answer, sample: true });
  }
});

test("an unsupported local question gets an explanation instead of an unrelated sample", async ({ request }) => {
  for (const endpoint of ["/api/ask", "/api/ask/stream"]) {
    const response = await request.post(endpoint, { data: { org: "FalkorDB", question: "An uncached custom question" } });
    expect(response.status()).toBe(400);
    expect((await response.json()).error).toContain("five suggested questions");
  }
});

test("all five starters show their own complete graph, Path and Cypher", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".react-flow__node")).toHaveCount(graphSchema().nodes.length);
  for (const { question, answer } of saved.answers) {
    await page.locator(".question-suggestions button").filter({ hasText: question }).click();
    await expect(page.getByRole("heading", { level: 1, name: question, exact: true })).toBeVisible();
    await expect(page.locator(".answer-meta")).toContainText("Saved production answer");
    await expect(page.locator(".react-flow__node")).toHaveCount(answer.evidence.nodes.length);
    await expect(page.locator(".react-flow__edge-path")).toHaveCount(answer.evidence.edges.length);
    expect(await page.locator(".react-flow__node").evaluateAll(nodes => nodes.map(n => n.getAttribute("data-id")).sort())).toEqual(answer.evidence.nodes.map(n => n.id).sort());
    await page.getByRole("tab", { name: /^Path/ }).click();
    await expect(page.getByRole("list", { name: "Evidence path through the graph" }).locator(":scope > li")).toHaveCount(answer.evidence.nodes.length);
    await page.getByRole("tab", { name: /^Cypher/ }).click();
    await expect(page.getByRole("tabpanel").locator("pre")).toHaveCount(answer.cypher.length);
    await page.getByRole("button", { name: "Back to questions" }).click();
  }
});
