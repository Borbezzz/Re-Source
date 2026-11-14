import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const artifacts = ".impeccable/review/prepared-demo";

test("prepared demo uses the real intake, batch, evidence, decision and approval screens", async ({
  page,
}) => {
  const errors: string[] = [];
  const writes: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (
      ["POST", "PATCH"].includes(request.method()) &&
      request.url().includes("/api/v1/")
    )
      writes.push(`${request.method()} ${new URL(request.url()).pathname}`);
  });
  await mkdir(artifacts, { recursive: true });
  await page.goto("/");
  const created = page.waitForResponse(
    (response) =>
      response.url().endsWith("/scenario-runs") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Start demo", exact: true }).click();
  const run = await (await created).json();
  const guide = page.getByRole("complementary", {
    name: "Prepared demo guide",
  });
  await expect(guide).toContainText(
    "Isolated run · synthetic data · real workflow",
  );
  await expect(
    page.getByRole("heading", { name: "Start with the source." }),
  ).toBeVisible();
  await expect(
    guide.getByRole("button", { name: "2 Assembly" }),
  ).toBeDisabled();
  await page.screenshot({ path: `${artifacts}/01-upload.png`, fullPage: true });

  await guide
    .getByRole("button", { name: "Upload & extract sample sources" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Review extracted fields" }),
  ).toBeVisible();
  await expect(page.getByLabel("Part number · required")).toHaveValue(
    "RS-FN-1001",
  );
  await expect(page.locator(".source-preview")).toContainText(
    "SYNTHETIC PREPARED DEMO",
  );
  await expect(page.getByLabel("Key dimensions", { exact: true })).toHaveValue(
    /12 mm/,
  );
  await page.reload();
  await expect(guide).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Review extracted fields" }),
  ).toBeVisible();
  await page
    .getByLabel("Description", { exact: true })
    .fill("Synthetic reviewer correction for the prepared demo.");
  await expect(
    page.getByRole("button", { name: "Confirm requirements", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Save corrections", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Confirm requirements", exact: true })
    .click();
  await expect(guide.getByRole("button", { name: "2 Assembly" })).toBeEnabled();
  await page
    .getByRole("button", { name: "Generate assembly", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "A mesh-generation provider is required.",
    }),
  ).toBeVisible();
  await expect(page.locator(".mesh-job")).toContainText(
    "No 3D mesh has been generated",
  );
  await page.screenshot({
    path: `${artifacts}/02-reviewed-real-provider-gap.png`,
    fullPage: true,
  });

  await guide
    .getByRole("button", { name: "Explore the prepared assembly" })
    .click();
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-ready",
    "true",
  );
  await page.getByRole("button", { name: "Explode", exact: true }).click();
  await expect(
    page.getByRole("slider", { name: "Assembly separation" }),
  ).toHaveValue("1");
  await page.locator(".component-list button").first().click();
  await expect(page.locator(".inspector h2")).toHaveText("Fuel nozzle");
  await expect(
    page.getByRole("button", { name: "Investigate suppliers", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: `${artifacts}/03-assembly-selection.png`,
    fullPage: true,
  });
  await guide
    .getByRole("button", { name: "Choose parts for investigation" })
    .click();
  await page.locator(".batch-part-options button").nth(0).click();
  await page.locator(".batch-part-options button").nth(1).click();
  await page
    .getByRole("button", { name: "Investigate 2 parts", exact: true })
    .click();
  await expect(page).toHaveURL(/#batch\//);
  await expect(
    page.locator(".batch-task-grid article>header .status"),
  ).toHaveText(["completed", "completed"]);
  await expect(page.locator(".finding-list button")).toHaveCount(8);
  await page.locator(".finding-list button").first().click();
  await page.locator(".finding-layout aside .citation").first().click();
  await expect(
    page.getByRole("region", { name: "Evidence detail" }),
  ).toBeVisible();
  await page.screenshot({
    path: `${artifacts}/04-parallel-investigation-evidence.png`,
    fullPage: true,
  });
  await page.keyboard.press("Escape");
  await page
    .locator(".batch-task-grid article")
    .first()
    .getByRole("button", { name: "Review options & decision" })
    .click();
  await expect(page.locator(".comparison-table tbody tr")).toHaveCount(5);
  await expect(
    guide.getByRole("button", { name: "4 Comparison & evidence" }),
  ).toHaveAttribute("aria-current", "step");
  await page.screenshot({
    path: `${artifacts}/05-comparison.png`,
    fullPage: true,
  });
  await page
    .locator(".comparison-table tbody tr")
    .first()
    .getByRole("button", { name: "Review", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Select & prepare pack", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Review the approval pack" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Simulate submission", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Approve package", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Simulate submission", exact: true }),
  ).toBeEnabled();
  await page
    .locator(".draft textarea")
    .first()
    .fill("Synthetic demo review: changed after approval.");
  await page
    .getByRole("button", { name: "Save field edits", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "Simulate submission", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Approve package", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Simulate submission", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Receipt recorded" }),
  ).toBeVisible();
  await page.screenshot({
    path: `${artifacts}/06-versioned-pack-simulated-receipt.png`,
    fullPage: true,
  });
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Receipt recorded" }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.screenshot({
    path: `${artifacts}/07-mobile-pack.png`,
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await guide.getByRole("button", { name: "Hide guide" }).click();
  await expect(guide.getByRole("button", { name: "Show guide" })).toBeVisible();
  await guide.getByRole("button", { name: "Exit demo guide" }).click();
  await expect(guide).not.toBeVisible();
  const active = await (
    await page.request.get("/api/v1/scenario-runs/current")
  ).json();
  expect(active.scenario_run_id).toBe(run.scenario_run_id);
  expect(
    writes.filter((write) => write === "POST /api/v1/intake/uploads"),
  ).toHaveLength(2);
  expect(writes).toContain("POST /api/v1/batches");
  expect(writes.some((write) => /\/selections$/.test(write))).toBe(true);
  expect(writes.some((write) => /\/simulated-submissions$/.test(write))).toBe(
    true,
  );
  expect(errors).toEqual([]);
});

test("immediate demo start waits for visitor bootstrap and failed extraction retries within its run", async ({
  page,
}) => {
  let release!: () => void;
  const bootstrap = new Promise<void>((resolve) => {
    release = resolve;
  });
  let firstEngine = true,
    newRuns = 0,
    uploads = 0;
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/scenario-runs"))
      newRuns += 1;
    if (
      request.method() === "POST" &&
      request.url().endsWith("/intake/uploads")
    )
      uploads += 1;
  });
  await page.route("**/api/v1/engines/engine-demo-001", async (route) => {
    if (firstEngine) {
      firstEngine = false;
      await bootstrap;
    }
    await route.continue();
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Start demo", exact: true }).click();
  await expect(
    page.getByText("Creating an isolated prepared-demo run…"),
  ).toBeVisible();
  expect(newRuns).toBe(0);
  release();
  const guide = page.getByRole("complementary", {
    name: "Prepared demo guide",
  });
  await expect(guide).toBeVisible();
  expect(newRuns).toBe(1);
  let fail = true;
  await page.route("**/api/v1/intake/part-requirements", async (route) => {
    if (fail) {
      fail = false;
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({
          code: "DEMO_TEST_RETRY",
          message: "Extraction temporarily unavailable",
          retryable: true,
        }),
      });
    } else await route.continue();
  });
  await guide
    .getByRole("button", { name: "Upload & extract sample sources" })
    .click();
  await expect(guide.getByRole("alert")).toContainText(
    "Extraction temporarily unavailable",
  );
  await guide
    .getByRole("button", { name: "Upload & extract sample sources" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Review extracted fields" }),
  ).toBeVisible();
  expect(uploads).toBe(2);
  const state = await page.evaluate(() =>
    JSON.parse(sessionStorage.getItem("resource:prepared-demo:v1") ?? "null"),
  );
  const current = await (
    await page.request.get("/api/v1/scenario-runs/current")
  ).json();
  expect(state.runId).toBe(current.scenario_run_id);
  expect(state.draftId).toBeTruthy();
});
