import { expect, test } from "@playwright/test";
import { graphSchema } from "../lib/graph-schema";

const SCHEMA_NODES = graphSchema().nodes.length;

test("the reading area reaches the panel edge, hides scrollbar chrome, and still scrolls", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Who knows the falkordb-py/ }).click();
  await page.getByRole("tab", { name: /^Cypher/ }).click();
  const panel = page.getByRole("tabpanel");
  await expect(panel).toHaveCSS("scrollbar-width", "none");
  const [reading, sidebar] = [await panel.boundingBox(), await page.locator(".workspace-sidebar").boundingBox()];
  expect(Math.abs(reading!.x + reading!.width - sidebar!.x - sidebar!.width)).toBeLessThanOrEqual(1);
  await panel.focus();
  await page.keyboard.press("PageDown");
  await expect.poll(() => panel.evaluate(el => el.scrollTop)).toBeGreaterThan(0);
  const selected = page.getByRole("tab", { name: /^Cypher/ });
  const borders = await selected.evaluate(el => { const css = getComputedStyle(el); return [css.borderTopWidth, css.borderBottomWidth]; });
  expect(borders[0]).toBe(borders[1]);
  await page.getByRole("tab", { name: "Answer", exact: true }).press("ArrowRight");
  await expect(page.getByRole("tab", { name: /^Path/ })).toHaveAttribute("aria-selected", "true");
});

test("question and answer screens crossfade without replacing the graph", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".react-flow__node")).toHaveCount(SCHEMA_NODES);
  const graph = await page.locator(".network-canvas").elementHandle();
  const transition = page.evaluate(() => new Promise<boolean>(resolve => {
    const started = performance.now();
    const sample = () => {
      const incoming = document.querySelector('[data-screen="answer"]');
      const opacity = incoming ? Number(getComputedStyle(incoming).opacity) : 1;
      if (incoming && opacity > 0 && opacity < 1) return resolve(true);
      if (performance.now() - started > 2000) return resolve(false);
      requestAnimationFrame(sample);
    };
    requestAnimationFrame(sample);
  }));
  await page.getByRole("button", { name: /Who knows the falkordb-py/ }).click();
  expect(await transition).toBe(true);
  await expect(page.locator('[data-screen="answer"]')).toHaveCSS("opacity", "1");
  await expect(page.locator(".workspace-screen")).toHaveCount(1);
  expect(await graph!.evaluate(el => el.isConnected)).toBe(true);
  await page.getByRole("button", { name: "Back to questions" }).click();
  await expect(page.getByRole("textbox", { name: "Your question" })).toBeFocused();
  await expect(page.locator('[data-screen="start"]')).toHaveCSS("opacity", "1");
});

test("tab content crossfades from the top without moving the graph", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Who knows the falkordb-py/ }).click();
  await expect(page.locator(".workspace-screen")).toHaveCount(1);
  const graph = await page.locator(".network-canvas").elementHandle();
  const transition = page.evaluate(() => new Promise<boolean>(resolve => {
    const started = performance.now();
    const sample = () => {
      const incoming = document.querySelector("#content-path");
      const opacity = incoming ? Number(getComputedStyle(incoming).opacity) : 1;
      if (incoming && opacity > 0 && opacity < 1) return resolve(true);
      if (performance.now() - started > 2000) return resolve(false);
      requestAnimationFrame(sample);
    };
    requestAnimationFrame(sample);
  }));
  await page.getByRole("tab", { name: /^Path/ }).click();
  expect(await transition).toBe(true);
  await expect(page.getByRole("tabpanel")).toHaveCSS("opacity", "1");
  await expect(page.locator(".workspace-content")).toHaveCount(1);
  expect(await graph!.evaluate(el => el.isConnected)).toBe(true);
  await page.getByRole("tabpanel").focus();
  await page.keyboard.press("PageDown");
  await expect.poll(() => page.getByRole("tabpanel").evaluate(el => el.scrollTop)).toBeGreaterThan(0);
  await page.getByRole("tab", { name: /^Cypher/ }).click();
  expect(await page.getByRole("tabpanel").evaluate(el => el.scrollTop)).toBe(0);
});

test("reduced motion removes panel and tab movement", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.getByRole("button", { name: /Who knows the falkordb-py/ }).click();
  await expect(page.locator('[data-screen="answer"]')).toHaveCSS("opacity", "1");
  await page.getByRole("tab", { name: /^Path/ }).click();
  await expect(page.getByRole("tabpanel")).toHaveCSS("opacity", "1");
  await expect(page.getByRole("tabpanel")).toHaveCSS("transform", "none");
});
