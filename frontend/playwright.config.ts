import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 180_000,
  expect: { timeout: 60_000 },
  workers: 1,
  use: {
    baseURL: process.env.RESOURCE_BASE_URL || "http://127.0.0.1:5173",
    viewport: { width: 1440, height: 900 },
    trace: "retain-on-failure",
  },
  reporter: "list",
});
