// Smoke tests for the ask flow. They run against saved production answers (AEVION_API_URL
// cleared), so they need no API, no graph and no LLM spend.
import { defineConfig, devices } from "@playwright/test";

const PORT = 43879;
const externalServer = process.env.PLAYWRIGHT_BASE_URL;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: externalServer ?? `http://localhost:${PORT}`,
    trace: "retain-on-failure",
    channel: process.env.PLAYWRIGHT_CHANNEL,
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: externalServer ? undefined : {
    // A production build: closer to what ships, and it can run beside a `next dev` session.
    command: `pnpm build && pnpm start --port ${PORT}`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    env: { AEVION_API_URL: "" },
    timeout: 240_000,
  },
});
