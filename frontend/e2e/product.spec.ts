import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
test("prepared product supports real geometry, reversible separation, multiple selection and reduced motion", async ({
  page,
}) => {
  await page.route("**/api/v1/**", (r) => r.abort());
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.locator(".product-scene")).toHaveAttribute(
    "data-ready",
    "true",
  );
  await expect(page.locator(".prepared-part-list button")).toHaveCount(8);
  await mkdir(".impeccable/review/v2", { recursive: true });
  await page.mouse.move(500, 210);
  await page.screenshot({ path: ".impeccable/review/v2/desktop.png" });
  const range = await page.locator(".assembly-track").evaluate((e) => ({
    start: e.offsetTop - 72,
    end: e.offsetTop + e.offsetHeight - innerHeight,
  }));
  for (const [name, p] of [
    ["assembled", 0],
    ["mid", 0.5],
    ["exploded", 1],
    ["reverse", 0],
  ] as const) {
    await page.evaluate(
      (y) => scrollTo({ top: y, behavior: "instant" }),
      range.start + (range.end - range.start) * p,
    );
    await expect
      .poll(async () =>
        Math.abs(
          Number(
            await page
              .locator(".product-scene")
              .getAttribute("data-separation"),
          ) - p,
        ),
      )
      .toBeLessThan(0.03);
    await page.screenshot({ path: `.impeccable/review/v2/${name}.png` });
  }
  await page.getByRole("button", { name: "Body shell", exact: true }).click();
  await page.screenshot({ path: ".impeccable/review/v2/selected-one.png" });
  await page
    .getByRole("button", { name: "Front left wheel", exact: true })
    .click();
  await expect(page.locator(".selection-tray")).toContainText(
    "2 parts selected",
  );
  await page.screenshot({ path: ".impeccable/review/v2/selected.png" });
  await page
    .getByRole("button", { name: "Remove Body shell", exact: true })
    .click();
  await expect(page.locator(".selection-tray")).toContainText(
    "1 part selected",
  );
  await page
    .getByRole("button", { name: "Window glazing", exact: true })
    .focus();
  await page.keyboard.press("Space");
  await expect(page.locator(".selection-tray")).toContainText(
    "2 parts selected",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.evaluate(() => scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({ path: ".impeccable/review/v2/mobile.png" });
  await page.getByRole("button", { name: "Explode", exact: true }).click();
  await expect(page.locator(".product-scene")).toHaveAttribute(
    "data-separation",
    "1.000",
  );
  await page.screenshot({ path: ".impeccable/review/v2/mobile-exploded.png" });
  await page.getByRole("button", { name: "Assemble", exact: true }).click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});

test("failed prepared asset keeps parts usable and ends loading", async ({
  page,
}) => {
  await page.route("**/api/v1/**", (r) => r.abort());
  await page.route("**/models/toy-car.glb", (r) => r.abort());
  await page.goto("/");
  await expect(page.locator(".product-scene")).toHaveAttribute(
    "data-status",
    "error",
  );
  await expect(
    page.getByText("Loading the prepared assembly…"),
  ).not.toBeVisible();
  await page.getByRole("button", { name: "Body shell", exact: true }).click();
  await expect(page.locator(".selection-tray")).toContainText(
    "1 part selected",
  );
  await page.locator(".assembly-track").scrollIntoViewIfNeeded();
  await page.screenshot({ path: ".impeccable/review/v2/failed-asset.png" });
});
