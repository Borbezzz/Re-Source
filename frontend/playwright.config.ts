import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  // Connected runs include queue cold starts and actual provider requests.
  timeout: process.env.RESOURCE_BASE_URL ? 420_000 : 180_000,
  expect: { timeout: process.env.RESOURCE_BASE_URL ? 180_000 : 60_000 },
  workers: 1,
  use: {
    channel: process.env.RESOURCE_BROWSER_CHANNEL || undefined,
    headless: !process.env.RESOURCE_HEADED,
    baseURL: process.env.RESOURCE_BASE_URL || "http://127.0.0.1:5173",
    viewport: { width: 1440, height: 900 },
    trace: "retain-on-failure",
  },
  reporter: "list",
});
