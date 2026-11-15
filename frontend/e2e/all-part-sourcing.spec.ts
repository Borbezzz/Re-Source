import { test, expect } from "@playwright/test";
import { fileURLToPath } from "node:url";

test.use({ channel: process.env.RESOURCE_BROWSER_CHANNEL || undefined, headless: !process.env.RESOURCE_HEADED });
const archive = fileURLToPath(new URL("../../blueprint input/mechanica-input-package.zip", import.meta.url));

test("full upload exposes sourcing for rings, housings, nozzle pieces and fasteners without availability badges", async ({ page }, info) => {
  test.setTimeout(120_000);
  await page.emulateMedia({ reducedMotion: "reduce" });
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/");
  await page.locator('input[type="file"]').first().setInputFiles(archive);
  await page.getByRole("button", { name: "Confirm and open assembly", exact: true }).click();
  await expect(page.getByRole("complementary", { name: "Assembly parts" })).toBeVisible();
  await expect(page.getByText("Demo sourcing available", { exact: true })).toHaveCount(0);
  await expect(page.locator(".rs-part-source")).toHaveCount(0);

  const inspect = async (name: string) => {
    await page.getByRole("button", { name, exact: true }).click();
    const card = page.getByRole("region", { name: `${name} actions`, exact: true });
    await expect(card.getByRole("button", { name: /^Replace faulty part/ })).toBeVisible();
    await expect(card.getByRole("button", { name: /^Change supplier/ })).toBeVisible();
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
  await casing.getByRole("button", { name: "Fastener 01", exact: true }).click();
  const fastener = page.getByRole("region", { name: "Fastener 01 actions", exact: true });
  await expect(fastener).toBeVisible();
  await expect(fastener).toHaveCSS("opacity", "1");
  await page.screenshot({ path: info.outputPath("fastener-sourcing.png") });
  await fastener.getByRole("button", { name: /^Change supplier/ }).click();
  await page.getByRole("button", { name: "Find suppliers", exact: true }).click();
  await expect(page.locator(".rs-map [data-pin]")).toHaveCount(8);
  await expect(page.getByText("Demo sourcing agent", { exact: true })).toBeVisible();
  await page.screenshot({ path: info.outputPath("fastener-suppliers.png") });
  expect(errors).toEqual([]);
});
