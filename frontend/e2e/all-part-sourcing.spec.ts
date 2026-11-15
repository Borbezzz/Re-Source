import { test, expect } from "@playwright/test";
import { fileURLToPath } from "node:url";

test.use({ channel: process.env.RESOURCE_BROWSER_CHANNEL || undefined, headless: !process.env.RESOURCE_HEADED });
const archive = fileURLToPath(new URL("../../blueprint input/mechanica-input-package.zip", import.meta.url));

test("full upload exposes sourcing for rings, housings, nozzle pieces and fasteners without availability badges", async ({ page }, info) => {
  test.setTimeout(300_000);
  await page.emulateMedia({ reducedMotion: "reduce" });
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/");
  await page.locator('input[type="file"]').first().setInputFiles(archive);
  const form = page.locator(".rs-risk-needs");
  await form.getByLabel("Delivery destination").fill("Bristol, UK");
  await form.getByLabel("Need-by date").fill("2026-11-24");
  const confirmed = page.waitForResponse(r => r.url().endsWith("/supply-risk/confirm") && r.request().method() === "POST");
  await form.getByRole("button", { name: "Confirm parts and scan supply risk", exact: true }).click();
  expect((await confirmed).ok()).toBeTruthy();
  await expect(page.getByRole("region", { name: "Supply-risk scan", exact: true })).toBeVisible();
  await expect(page.getByRole("complementary", { name: "Assembly parts" })).toBeVisible();
  await expect(page.getByText("Demo sourcing available", { exact: true })).toHaveCount(0);
  await expect(page.locator(".rs-part-source")).toHaveCount(0);

  const inspect = async (name: string) => {
    await page.getByRole("button", { name: `${name} Arrival unknown`, exact: true }).click();
    const risk = page.locator(".rs-risk-panel");
    await expect(risk).toBeVisible();
    await risk.getByRole("button", { name: "Find alternative suppliers" }).click();
    const card = page.getByRole("region", { name: `${name} actions`, exact: true });
    // RiskPanel now opens ContextCard directly in need mode, not action mode.
    await expect(card.getByLabel("Required on site by")).toHaveValue("2026-11-24");
    await expect(card.getByRole("button", { name: "Find suppliers", exact: true })).toBeVisible();
    await card.getByRole("button", { name: "Clear selection", exact: true }).click();
    await expect(card).toBeHidden();
  };
  await inspect("Fan retaining ring");
  for (const [assembly, part] of [["compressor", "Compressor housing"], ["nozzle", "Nozzle housing 01"]]) {
    await page.locator(`[data-part-id="rs-mech-tf-v1.group.${assembly}"] > .rs-part-row .rs-part-toggle`).click();
    if (assembly === "nozzle") await page.locator('[data-part-id="rs-mech-tf-v1.group.nozzle"]').getByRole("button", { name: "Expand Housings", exact: true }).click();
    await inspect(part);
  }
  const casing = page.locator('[data-part-id="rs-mech-tf-v1.group.casing"]');
  await casing.locator(':scope > .rs-part-row .rs-part-toggle').click();
  await casing.getByRole("button", { name: "Expand Fasteners", exact: true }).click();
  await casing.getByRole("button", { name: "Fastener 01 Arrival unknown", exact: true }).click();
  await page.locator(".rs-risk-panel").getByRole("button", { name: "Find alternative suppliers" }).click();
  const fastener = page.getByRole("region", { name: "Fastener 01 actions", exact: true });
  await expect(fastener).toBeVisible();
  await expect(fastener).toHaveCSS("opacity", "1");
  await page.screenshot({ path: info.outputPath("fastener-sourcing.png") });
  await expect(fastener.getByLabel("Required on site by")).toHaveValue("2026-11-24");
  await page.getByRole("button", { name: "Find suppliers", exact: true }).click();
  await expect(page.locator(".rs-map [data-pin]")).toHaveCount(8);
  await expect(page.getByText("Demo sourcing agent", { exact: true })).toBeVisible();
  await page.screenshot({ path: info.outputPath("fastener-suppliers.png") });
  expect(errors).toEqual([]);
});
