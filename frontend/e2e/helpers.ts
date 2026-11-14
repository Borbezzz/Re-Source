import { expect, type Page } from "@playwright/test";

// Use the browser context's cookie jar and the tested origin. A separate API
// fixture pointed at localhost would not exercise the public visitor boundary.
export async function startSeededRun(page: Page) {
  const response = await page.request.post("/api/v1/scenario-runs", {
    data: {
      mode: "seeded",
      manifest_id: "engine-demo-001",
      fixture_version: "seed-v1",
    },
  });
  expect(
    response.ok(),
    `Create seeded run: HTTP ${response.status()}`,
  ).toBeTruthy();
  return response.json();
}
