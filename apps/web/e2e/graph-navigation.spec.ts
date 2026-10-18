import { expect, test } from "@playwright/test";
import { sampleAnswer } from "../lib/sample-answer";
import { graphSchema } from "../lib/graph-schema";

const SCHEMA_NODES = graphSchema().nodes.length;

test("all returned nodes, including disconnected evidence, stay on the map", async ({ page }) => {
  const answer = sampleAnswer("test");
  answer.evidence.nodes.push({ id: "Person:isolated", label: "Person", title: "Isolated evidence", url: "https://github.com/example" });
  await page.route("**/api/ask/stream", route => route.fulfill({ contentType: "text/event-stream", body: `data: ${JSON.stringify({ type: "answer", answer })}\n\n` }));
  await page.goto("/");
  await page.getByRole("textbox", { name: "Your question" }).fill("Show all evidence");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("button", { name: "person: Isolated evidence", exact: true })).toBeVisible();
  await expect(page.locator(".react-flow__node")).toHaveCount(answer.evidence.nodes.length);
  await expect(page.getByRole("button", { name: "Fit all nodes" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Focus cited sources" })).toBeVisible();
});

test("the graph remains available while the next question is being answered", async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/api/ask/stream", async route => {
    await gate;
    await route.fulfill({ contentType: "text/event-stream", body: `data: ${JSON.stringify({ type: "answer", answer: sampleAnswer("test") })}\n\n` });
  });
  await page.goto("/");
  await page.getByRole("textbox", { name: "Your question" }).fill("A different question");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("list", { name: "What Aevion did" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Fit all nodes" })).toBeVisible();
  release();
  await expect(page.getByRole("button", { name: /^Source 1: / })).toBeVisible();
});

test("graph controls support zoom, source focus, and node search without removing nodes", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Who knows the falkordb-py/ }).click();
  await expect(page.locator(".react-flow__node")).toHaveCount(20);
  const canvas = page.locator(".react-flow__viewport");
  await expect(canvas).toBeVisible();
  const before = await canvas.getAttribute("style");
  await page.getByRole("button", { name: "Zoom in", exact: true }).click();
  await expect(canvas).not.toHaveAttribute("style", before!);
  const count = await page.locator(".react-flow__node").count();
  await page.getByRole("searchbox", { name: "Find a node" }).fill("gkorland");
  await page.getByRole("button", { name: "Find person: gkorland" }).click();
  await expect(page.getByRole("region", { name: "Selected node" })).toContainText("gkorland");
  await expect(page.locator(".react-flow__node")).toHaveCount(count);
  await page.getByRole("button", { name: "Fit all nodes" }).click();
  await expect(page.getByRole("button", { name: "Fullscreen graph" })).toBeVisible();
});

test("Fit all brings every returned node inside the canvas", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".react-flow__node")).toHaveCount(SCHEMA_NODES);
  await page.getByRole("button", { name: "Fit all nodes" }).click();
  await expect.poll(() => page.locator(".network-canvas").evaluate(canvas => {
    const bounds = canvas.getBoundingClientRect();
    return [...canvas.querySelectorAll(".react-flow__node")].every(node => {
      const rect = node.getBoundingClientRect();
      return rect.left >= bounds.left && rect.right <= bounds.right && rect.top >= bounds.top && rect.bottom <= bounds.bottom;
    });
  })).toBe(true);
});

test("a Path entry opens its matching node in Map", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Who knows the falkordb-py/ }).click();
  await page.getByRole("tab", { name: /^Path/ }).click();
  await page.getByRole("button", { name: "Show gkorland on map", exact: true }).click();
  await expect(page.getByRole("tab", { name: /^Path/ })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("region", { name: "Selected node" })).toContainText("gkorland");
});

test("a different answer replaces the evidence without replacing the canvas", async ({ page }) => {
  const answer = sampleAnswer("test");
  answer.answer = "A different recorded graph [1].";
  answer.evidence = { nodes: [{ id: "Person:new", label: "Person", title: "New evidence" }], edges: [] };
  answer.citations = [{ n: 1, node_id: "Person:new" }];
  await page.route("**/api/ask/stream", route => route.fulfill({ contentType: "text/event-stream", body: `data: ${JSON.stringify({ type: "answer", answer })}\n\n` }));
  await page.goto("/");
  await expect(page.locator(".react-flow__node")).toHaveCount(SCHEMA_NODES);
  const originalCanvas = await page.locator(".network-canvas").elementHandle();
  await page.getByRole("textbox", { name: "Your question" }).fill("Different evidence");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.locator(".react-flow__node")).toHaveCount(1);
  expect(await originalCanvas!.evaluate(el => el.isConnected)).toBe(true);
  await expect(page.getByRole("button", { name: "Source 1, person: New evidence", exact: true })).toBeVisible();
});

test("Fit all restores the whole graph after focusing a source and resizing", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Who knows the falkordb-py/ }).click();
  await expect(page.locator(".react-flow__node")).toHaveCount(20);
  await page.getByRole("searchbox", { name: "Find a node" }).fill("gkorland");
  await page.getByRole("button", { name: "Find person: gkorland" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Fit all nodes" }).click();
  await expect.poll(() => page.locator(".network-canvas").evaluate(canvas => {
    const bounds = canvas.getBoundingClientRect();
    return [...canvas.querySelectorAll(".react-flow__node")].every(node => {
      const rect = node.getBoundingClientRect();
      return rect.left >= bounds.left && rect.right <= bounds.right && rect.top >= bounds.top && rect.bottom <= bounds.bottom;
    });
  })).toBe(true);
});

test("background nodes stay visible in the overview and reveal labels when zooming", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Who knows the falkordb-py/ }).click();
  await expect(page.locator(".react-flow__node")).toHaveCount(20);
  const background = page.locator(".network-node.is-background").first();
  await expect(background).toBeVisible();
  await expect(background.locator(".network-node-label")).toBeHidden();
  for (let i = 0; i < 10; i++) {
    await page.getByRole("button", { name: "Zoom in", exact: true }).click();
    await page.waitForTimeout(750);
  }
  await expect(background.locator(".network-node-label")).toBeVisible();
  await expect(page.locator(".react-flow__node")).toHaveCount(20);
  await page.getByRole("button", { name: "Fit all nodes" }).click();
  await expect(background.locator(".network-node-label")).toBeHidden();
});

test("the larger triage map opens on its route, fits every node on request, and explains disconnected evidence", async ({ page }) => {
  await page.goto("/triage");
  await page.getByRole("button", { name: "FalkorDB/FalkorDB#3357 UDF reload races concurrent queries", exact: true }).click();
  await expect(page.locator(".react-flow__node")).toHaveCount(54);
  await expect(page.locator(".react-flow__edge")).toHaveCount(49);
  // A crowded map opens on the route, centred on the component the route runs through.
  await expect.poll(() => page.locator(".network-canvas").evaluate(canvas => {
    const c = canvas.getBoundingClientRect();
    // While the triage loads the map is drawn plain, with no anchor yet.
    const marked = canvas.querySelector(".network-node.is-anchor");
    if (!marked) return false;
    const anchor = marked.getBoundingClientRect();
    const inside = (r: DOMRect) => r.left >= c.left && r.right <= c.right && r.top >= c.top && r.bottom <= c.bottom;
    const route = [...canvas.querySelectorAll(".react-flow__node:has(.is-route)")].map(n => n.getBoundingClientRect());
    return route.every(inside) && Math.abs(anchor.left + anchor.width / 2 - (c.left + c.width / 2)) < 4;
  })).toBe(true);
  await page.getByRole("button", { name: "Fit all nodes" }).click();
  await expect.poll(() => page.locator(".network-canvas").evaluate(canvas => {
    const bounds = canvas.getBoundingClientRect();
    return [...canvas.querySelectorAll(".react-flow__node")].every(node => {
      const rect = node.getBoundingClientRect();
      return rect.left >= bounds.left && rect.right <= bounds.right && rect.top >= bounds.top && rect.bottom <= bounds.bottom;
    });
  })).toBe(true);
  await page.getByRole("searchbox", { name: "Find a node" }).fill("3357");
  await page.locator(".network-search-results button").click();
  await expect(page.getByRole("region", { name: "Selected node" })).toContainText("No connections returned for this node");
});

test("pointing at a starter lights the part of the graph model its answer walks, without moving the camera", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "mobile", "hover is a pointer affordance; checked on desktop");
  await page.goto("/");
  await expect(page.locator(".react-flow__node")).toHaveCount(SCHEMA_NODES);
  const viewport = () => page.locator(".react-flow__viewport").evaluate(el => el.style.transform);
  await page.waitForTimeout(900);
  const before = await viewport();
  await page.getByRole("button", { name: /Why did FalkorDB gate main on a merge queue/ }).hover();
  await expect(page.locator(".react-flow__node[data-id='Schema:Decision'] .network-node")).toHaveClass(/is-linked/);
  await expect(page.locator(".network-node.is-dimmed").first()).toBeVisible();
  expect(await viewport()).toBe(before);
  await page.getByRole("heading", { level: 1 }).hover();
  await expect(page.locator(".network-node.is-linked")).toHaveCount(0);
  await expect(page.locator(".network-node.is-dimmed")).toHaveCount(0);
});

test("pointing at a triage starter lights the walk from similar issues to the code and its people", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "mobile", "hover is a pointer affordance; checked on desktop");
  await page.goto("/triage");
  await expect(page.locator(".react-flow__node")).toHaveCount(SCHEMA_NODES);
  await page.getByRole("button", { name: "FalkorDB/FalkorDB#3357 UDF reload races concurrent queries", exact: true }).hover();
  await expect(page.locator(".react-flow__node[data-id='Schema:Component'] .network-node")).toHaveClass(/is-linked/);
});
