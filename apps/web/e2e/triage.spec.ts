import { expect, test } from "@playwright/test";

test("a starter issue gets an area, an expert, a reply and proposed actions", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Triage" }).click();
  await expect(page.getByRole("heading", { name: "Triage an issue" })).toBeVisible();

  await page.getByRole("button", { name: /FalkorDB\/FalkorDB#3357/ }).click();
  const findings = page.getByRole("region", { name: "Triage result" });
  // The first finding is the area of the code.
  await expect(findings.locator("dd").first()).toContainText("src/udf");
  await expect(findings.getByRole("link", { name: "swilly22" }).first()).toBeVisible();
  await expect(findings.getByText("The reply Aevion would post")).toBeVisible();
  await expect(findings.getByText("Would do", { exact: true })).toHaveCount(3);
  await expect(findings.getByText(/@swilly22/)).toHaveCount(0); // names people, never pings them
});

test("acting is only possible on the sandbox repo", async ({ page }) => {
  await page.goto("/triage");
  const issue = page.getByRole("textbox", { name: "Issue key" });
  const act = page.getByRole("radio", { name: "Act on the issue" });

  await issue.fill("FalkorDB/FalkorDB#3357");
  await expect(act).toBeDisabled();
  await expect(page.getByRole("button", { name: "Triage", exact: true })).toBeEnabled();

  await issue.fill("hineshmiyani/aevion-sandbox#37");
  await expect(act).toBeEnabled();
  await act.check();
  await expect(page.getByRole("button", { name: "Triage and act" })).toBeVisible();

  await issue.fill("not a key");
  await expect(page.getByRole("button", { name: "Triage", exact: true })).toBeDisabled();
});

test("the triage page never scrolls sideways", async ({ page }) => {
  await page.goto("/triage");
  await page.getByRole("button", { name: /FalkorDB\/FalkorDB#3357/ }).click();
  await expect(page.getByText("What the graph says")).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
