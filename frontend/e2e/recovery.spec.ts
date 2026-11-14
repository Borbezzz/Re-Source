import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
test("source entry, real mesh selection, events, comparison and versioned approval", async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (e) => {
    if (e.type() === "error") errors.push(e.text());
  });
  await mkdir(".impeccable/review", { recursive: true });
  const run = await request.post("http://127.0.0.1:8000/api/v1/scenario-runs", {
    data: {
      mode: "seeded",
      manifest_id: "engine-demo-001",
      fixture_version: "seed-v1",
    },
  });
  expect(run.ok()).toBeTruthy();
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Start with the source." }),
  ).toBeVisible();
  await page.screenshot({
    path: ".impeccable/review/intake-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Open seeded workspace" }).click();
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-ready",
    "true",
  );
  await expect(page.locator(".mesh-pin")).toHaveCount(3);
  await page.getByRole("button", { name: "Explode", exact: true }).click();
  await expect(
    page.getByRole("slider", { name: "Assembly separation" }),
  ).toHaveValue("1");
  await page
    .getByRole("button", {
      name: "Select Combustor fuel nozzle (position 7)",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "Fuel nozzle", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Review \d+ recovery options/ }),
  ).toBeVisible();
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-settled",
    "true",
  );
  await page.screenshot({
    path: ".impeccable/review/desktop.png",
    fullPage: false,
  });
  await page
    .getByRole("button", { name: /Review \d+ recovery options/ })
    .click();
  await expect(page.locator(".comparison-table tbody tr")).toHaveCount(5);
  await expect(page.locator(".map-sites button")).toHaveCount(5);
  await page.screenshot({
    path: ".impeccable/review/research-desktop.png",
    fullPage: true,
  });
  await page
    .locator(".comparison-table tbody tr")
    .first()
    .getByRole("button", { name: "Review", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Select & prepare pack" }),
  ).toBeEnabled();
  await page.locator(".checks details").first().locator("summary").click();
  await page.locator(".candidate-detail .citation:visible").first().click();
  await expect(
    page.getByRole("region", { name: "Evidence detail" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("region", { name: "Evidence detail" }),
  ).not.toBeVisible();
  await page.getByRole("button", { name: "Select & prepare pack" }).click();
  await expect(
    page.getByRole("heading", { name: "Review the approval pack" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Simulate submission" }),
  ).toBeDisabled();
  await page.screenshot({
    path: ".impeccable/review/documents-desktop.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Approve package", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Simulate submission" }),
  ).toBeEnabled();
  const editable = page.locator(".draft textarea").first();
  await editable.fill("Frontend verification: synthetic review edit");
  await page.getByRole("button", { name: "Save field edits" }).first().click();
  await expect(
    page.getByRole("button", { name: "Simulate submission" }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Approve package", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Simulate submission" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Simulate submission" }).click();
  await expect(
    page.getByRole("heading", { name: "Receipt recorded" }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({
    path: ".impeccable/review/documents-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Suppliers", exact: true }).click();
  await expect(page.locator(".comparison-table tbody tr")).toHaveCount(5);
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({
    path: ".impeccable/review/research-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});
test("narrow viewport and reduced motion retain keyboard/direct controls", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.screenshot({
    path: ".impeccable/review/intake-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Open seeded workspace" }).click();
  await expect(page.getByLabel("Reduced motion enabled")).toBeDisabled();
  await page.getByRole("button", { name: "Explode", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("slider", { name: "Assembly separation" }),
  ).toHaveValue("1");
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-ready",
    "true",
  );
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-settled",
    "true",
  );
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({
    path: ".impeccable/review/mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});

test("scroll reverses explosion and disruption publishes a new decision with repair gates intact", async ({
  page,
  request,
}) => {
  await request.post("http://127.0.0.1:8000/api/v1/scenario-runs", {
    data: {
      mode: "seeded",
      manifest_id: "engine-demo-001",
      fixture_version: "seed-v1",
    },
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Open seeded workspace" }).click();
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-ready",
    "true",
  );
  await page.evaluate(() => window.scrollTo({ top: 700, behavior: "instant" }));
  await expect
    .poll(async () =>
      Number(
        await page
          .getByRole("slider", { name: "Assembly separation" })
          .inputValue(),
      ),
    )
    .toBeGreaterThan(0.2);
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await expect
    .poll(async () =>
      Number(
        await page
          .getByRole("slider", { name: "Assembly separation" })
          .inputValue(),
      ),
    )
    .toBeLessThan(0.05);
  await page.locator(".component-list button").first().click();
  await expect(
    page.getByRole("button", { name: /Review \d+ recovery options/ }),
  ).toBeVisible();
  await page.locator(".recovery-controls summary").click();
  await expect(page.getByRole("button", { name: /^install$/i })).toBeDisabled();
  await expect(page.getByRole("button", { name: /^restore$/i })).toBeDisabled();
  await page
    .getByRole("button", { name: /Review \d+ recovery options/ })
    .click();
  await page.getByRole("button", { name: "Introduce port closure" }).click();
  await expect(page.locator(".decision-diff")).toContainText(
    "What changed since the initial decision",
  );
  await expect(page.locator(".comparison .section-heading")).toContainText(
    "D2",
  );
  await page
    .getByRole("button", { name: "Assembly", exact: true })
    .last()
    .click();
  await page.locator(".component-list button").nth(1).click();
  await expect(page.locator(".inspector h2")).toHaveText("NGV segment");
  await expect(
    page.getByRole("button", { name: /Review \d+ recovery options/ }),
  ).toBeVisible();
  await expect(page.locator(".inspector")).not.toContainText("Fuel nozzle");
});
