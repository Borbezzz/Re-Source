import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";

test("first load renders a real engine without API readiness and reverses its scroll sequence", async ({
  page,
}) => {
  // The API is unavailable; no fake run or supplier results are injected.
  await page.route("**/api/v1/**", (route) => route.abort());
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await mkdir(".impeccable/review", { recursive: true });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  {
    await expect(page.locator(".intro-canvas canvas")).toBeVisible();
    await expect(page.locator(".scene-root")).toHaveAttribute(
      "data-ready",
      "true",
    );
    await expect(page.locator(".module-strip button")).toHaveCount(7);
    await expect(page.locator(".intro-parts button").first()).toBeDisabled();
    const extent = await page
      .locator(".intro-scroll")
      .evaluate((el) => el.offsetTop + el.offsetHeight - innerHeight);
    for (const [name, progress] of [
      ["assembled", 0],
      ["mid", 0.5],
      ["exploded", 1],
      ["reverse", 0],
    ] as const) {
      await page.evaluate(
        (y) => scrollTo({ top: y, behavior: "instant" }),
        extent * progress,
      );
      await expect
        .poll(async () =>
          Math.abs(
            Number(
              await page.locator(".scene-root").getAttribute("data-separation"),
            ) - progress,
          ),
        )
        .toBeLessThan(progress === 0.5 ? 0.1 : 0.02);
      await expect(page.locator(".scene-root")).toHaveAttribute(
        "data-settled",
        "true",
      );
      await page.screenshot({ path: `.impeccable/review/intro-${name}.png` });
    }
    await page
      .getByRole("button", { name: "04 Combustor", exact: true })
      .click();
    await expect(page.locator(".intro-module-detail h2")).toHaveText(
      "Combustor",
    );
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole("button", { name: "Close details ×" }).click();
    await page.screenshot({ path: ".impeccable/review/intro-mobile.png" });
    await page
      .getByRole("button", { name: "Parts, requirements & source upload" })
      .click();
    await expect(
      page.getByRole("button", { name: "Upload source documents" }),
    ).toBeVisible();
    await expect(page.locator(".intro-requirements")).toContainText(
      "Source required",
    );
    await page.screenshot({
      path: ".impeccable/review/intro-mobile-details.png",
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    expect(errors).toEqual([]);
  }
});
