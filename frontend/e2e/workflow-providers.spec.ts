import { test, expect } from "@playwright/test";
import { fileURLToPath } from "node:url";

test.use({ channel: process.env.RESOURCE_BROWSER_CHANNEL || undefined, headless: !process.env.RESOURCE_HEADED });
const archive = fileURLToPath(new URL("../../blueprint input/mechanica-input-package.zip", import.meta.url));

test("workflow names provider features without claiming demo calls ran", async ({ page }, info) => {
  test.setTimeout(150_000);
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.locator('input[type="file"]').first().setInputFiles(archive);
  await page.getByRole("button", { name: "Confirm and open assembly", exact: true }).click();
  await page.getByRole("button", { name: "Expand Fan blades", exact: true }).click();
  await page.getByRole("button", { name: "Fan blade 03", exact: true }).click();
  await page.getByRole("button", { name: /^Change supplier/ }).click();
  await page.getByRole("button", { name: "Find suppliers", exact: true }).click();
  await page.getByRole("button", { name: "Compare shortlist", exact: true }).click();
  const response = page.waitForResponse(r => r.url().endsWith("/package") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Select supplier", exact: true }).click();
  const project = await (await response).json();
  await expect(page.locator(".rs-fulfil")).toHaveCSS("opacity", "1");
  expect(project.research[0].providers_used).toEqual(["prepared_demo"]);
  const storage = project.capabilities.storage === "lakebase_postgres" ? "Databricks Lakebase · Postgres" : "Local SQLite";
  const output = page.getByRole("region", { name: "Stage output" });
  for (const [id, title, detail] of [
    ["trigger", project.capabilities.storage === "lakebase_postgres" ? "Lakebase · Save case" : "Save sourcing case", storage],
    ["discover", "Linkup · Web Search", "Prepared demo offers; Linkup was not called"],
    ["extract", "Databricks · ai_extract", "Prepared demo claims; ai_extract was not called"],
    ["rank", "Rank shortlist", "Re::Source weighted scoring"],
    ["approve", "Approve RFQ", storage],
  ]) {
    await page.locator(`[data-step="${id}"] > button`).click();
    await expect(output.locator(".fl-out-title")).toHaveText(title);
    await expect(output).toContainText(detail);
    if (id === "discover" || id === "extract") {
      await expect(output.locator(".fl-insp-status")).toHaveText("Skipped");
      await expect(page.locator(`[data-step="${id}"] > button`)).toHaveAttribute("data-status", "skipped");
    }
    if (id === "trigger") await expect(output).toContainText("Databricks ai_parse_document");
    if (id === "extract") {
      await expect(output.locator(".fl-out-body")).toHaveCSS("opacity", "1");
      await page.screenshot({ path: info.outputPath("databricks-workflow.png") });
    }
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('[data-step="extract"] > button').click();
  const inspector = page.getByRole("complementary", { name: "Databricks · ai_extract details" });
  await expect(inspector).toContainText("Prepared demo claims; ai_extract was not called");
  await expect(inspector).toHaveCSS("opacity", "1");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const titleBox = await page.locator(".fl-bar-title").boundingBox();
  const controlsBox = await page.locator(".fl-bar .fl-modes").boundingBox();
  expect(titleBox!.x + titleBox!.width).toBeLessThanOrEqual(controlsBox!.x);
  await page.screenshot({ path: info.outputPath("databricks-workflow-mobile.png") });
  expect(errors).toEqual([]);
});
