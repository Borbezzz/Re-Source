import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { startSeededRun } from "./helpers";
test("parallel component research replays real findings, sources and per-part activity", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await startSeededRun(page);
  await page.goto("/#investigations");
  await expect(page.locator(".batch-part-options button")).toHaveCount(3);
  await page.locator(".batch-part-options button").nth(0).click();
  await page.locator(".batch-part-options button").nth(1).click();
  await mkdir(".impeccable/review/batch", { recursive: true });
  await page.screenshot({ path: ".impeccable/review/batch/start.png" });
  await page
    .getByRole("button", { name: "Investigate 2 parts", exact: true })
    .click();
  await expect(page).toHaveURL(/#batch\//);
  const url = page.url();
  await expect(page.locator(".batch-task-grid article")).toHaveCount(2);
  await expect(page.locator(".research-globe")).toHaveAttribute(
    "data-ready",
    "true",
  );
  await expect(page.locator(".finding-list button")).toHaveCount(8);
  await expect(
    page.locator(".batch-task-grid article>header .status"),
  ).toHaveText(["completed", "completed"]);
  await expect(page.locator(".activity-part-label").first()).not.toBeEmpty();
  await expect(page.locator(".event-list")).toContainText(
    "Investigation finished",
  );
  await page.screenshot({
    path: ".impeccable/review/batch/desktop.png",
    fullPage: true,
  });
  await page.locator(".batch-filters button").nth(1).click();
  await expect(page.locator(".finding-list button")).toHaveCount(5);
  await expect(page.locator(".batch-task-grid article")).toHaveCount(1);
  await page.locator(".finding-list button").first().click();
  await expect(page.locator(".finding-layout aside")).toContainText(
    "synthetic demo",
  );
  await expect(page.locator(".finding-layout aside")).toContainText(
    "representative",
  );
  await page.locator(".finding-layout aside .citation").first().click();
  await expect(
    page.getByRole("region", { name: "Evidence detail" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await page
    .getByRole("button", { name: "Investigations", exact: true })
    .click();
  await expect(page).toHaveURL(url);
  await page.reload();
  await expect(page).toHaveURL(url);
  await expect(page.locator(".finding-list button")).toHaveCount(8);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({
    path: ".impeccable/review/batch/mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Rotate globe left" }).click();
  await page
    .locator(".batch-task-grid article")
    .first()
    .getByRole("button", { name: "Review options & decision" })
    .click();
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-ready",
    "true",
  );
  expect(errors).toEqual([]);
});
test("unavailable batch stops loading and retries the full connection", async ({
  page,
}) => {
  await page.route("**/api/v1/batches/missing", (r) =>
    r.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({
        code: "NOT_FOUND",
        message: "Investigation not found",
        retryable: false,
      }),
    }),
  );
  await page.goto("/#batch/missing");
  await expect(page.getByRole("alert")).toContainText(
    "Investigation not found",
  );
  await expect(page.getByText("Loading investigation…")).not.toBeVisible();
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Investigation not found",
  );
});
