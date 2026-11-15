import { test, expect, type Page } from "@playwright/test";
import { fileURLToPath } from "node:url";

test.use({ channel: process.env.RESOURCE_BROWSER_CHANNEL || undefined, headless: !process.env.RESOURCE_HEADED });
const archive = fileURLToPath(new URL("../../blueprint input/mechanica-input-package.zip", import.meta.url));

async function openAssembly(page: Page) {
  await page.goto(process.env.RESOURCE_BASE_URL || "http://127.0.0.1:5173");
  await page.locator('input[type="file"]').first().setInputFiles(archive);
  const form = page.locator(".rs-risk-needs");
  await form.getByLabel("Delivery destination").fill("Bristol, UK");
  await form.getByLabel("Need-by date").fill("2026-11-24");
  const confirmed = page.waitForResponse(r => r.url().endsWith("/supply-risk/confirm") && r.request().method() === "POST");
  await form.getByRole("button", { name: "Confirm parts and scan supply risk", exact: true }).click();
  expect((await confirmed).ok()).toBeTruthy();
  await expect(page.getByRole("region", { name: "Supply-risk scan", exact: true })).toBeVisible();
  await expect(page.getByRole("complementary", { name: "Assembly parts" })).toBeVisible();
  await expect(page.locator(".rs-part-callout, .rs-hotspot")).toHaveCount(0);
}

/** Compare the DOM dot with the actual selected mesh's projected world bounds. */
async function anchorError(page: Page, stableId: string) {
  return page.evaluate(id => {
    const { prepared, camera } = (window as any).__rsScene;
    prepared.root.updateMatrixWorld(true);
    const node = prepared.byStable.get(id);
    const center = node.geometry.boundingBox.clone().applyMatrix4(node.matrixWorld).getCenter(node.position.clone()).project(camera);
    const canvas = document.querySelector(".rs-engine-canvas canvas")!.getBoundingClientRect();
    const dot = document.querySelector(".rs-part-callout-dot")!.getBoundingClientRect();
    return Math.hypot(dot.x + dot.width / 2 - canvas.x - (center.x + 1) * canvas.width / 2,
      dot.y + dot.height / 2 - canvas.y - (1 - center.y) * canvas.height / 2);
  }, stableId);
}

test("only the selected occurrence has a connected label, including small hardware", async ({ page }, info) => {
  test.setTimeout(300_000);
  await page.emulateMedia({ reducedMotion: "reduce" });
  const errors: string[] = [];
  page.on("pageerror", e => errors.push(e.message));
  await openAssembly(page);
  await page.getByRole("button", { name: /^Fan blades.*24/ }).hover();
  await expect(page.locator(".rs-part-callout, .rs-hotspot")).toHaveCount(0);
  await page.getByRole("button", { name: "Expand Fan blades", exact: true }).click();
  await page.getByRole("button", { name: /^Fan blade 07/ }).click();
  await expect(page.locator(".rs-part-callout")).toHaveCount(1);
  await expect(page.locator(".rs-part-callout-label")).toHaveText("Fan blade 07");
  await expect(page.locator(".rs-part-callout-leader path")).toBeVisible();
  await expect.poll(() => anchorError(page, "rs-mech-tf-v1.fan.m000.i006")).toBeLessThan(2);
  await page.evaluate(async () => { await (window as any).__rsScene.controls.rotate(0.45, 0.1, true); });
  await expect.poll(() => anchorError(page, "rs-mech-tf-v1.fan.m000.i006")).toBeLessThan(2);
  await page.screenshot({ path: info.outputPath("selected-blade.png") });
  await page.getByRole("button", { name: /^Fan blade 08/ }).click();
  await expect(page.locator(".rs-part-callout")).toHaveCount(1);
  await expect(page.locator(".rs-part-callout-label")).toHaveText("Fan blade 08");
  await expect.poll(() => anchorError(page, "rs-mech-tf-v1.fan.m000.i007")).toBeLessThan(2);
  await page.locator(".rs-risk-panel").getByRole("button", { name: "Close part risk panel", exact: true }).click();
  await expect(page.locator(".rs-part-callout, .rs-hotspot")).toHaveCount(0);
  await page.getByRole("button", { name: "Collapse Fan blades", exact: true }).click();
  await page.getByRole("button", { name: /^Fan and inlet 62/ }).click();
  await expect(page.locator(".rs-part-callout")).toHaveCount(1);
  await expect(page.locator(".rs-part-callout-label")).toHaveText("Fan and inlet");
  await page.getByRole("region", { name: "Fan and inlet inspection" }).getByRole("button", { name: "Clear selection", exact: true }).click();
  const fan = page.locator('[data-part-id="rs-mech-tf-v1.group.fan"]');
  await fan.getByRole("button", { name: "Fan retaining ring Arrival unknown", exact: true }).click();
  await expect(page.locator(".rs-risk-panel")).toBeVisible();
  await expect(page.locator(".rs-risk-panel").getByRole("button", { name: "Find alternative suppliers" })).toBeVisible();
  await expect(page.locator(".rs-part-callout-label")).toHaveText("Fan retaining ring");
  await page.locator(".rs-risk-panel").getByRole("button", { name: "Close part risk panel", exact: true }).click();
  await expect(page.locator(".rs-part-callout, .rs-hotspot")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("mobile selection keeps its label within the viewport", async ({ browser }, info) => {
  test.setTimeout(300_000);
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: "reduce" });
  const page = await context.newPage();
  await openAssembly(page);
  // The mobile overview intentionally covers the assembly tree and has no close
  // control. Select a single-mesh ring through the overview instead. This retains
  // mobile anchoring/bounds coverage, not the original third-blade tree interaction.
  await page.locator(".rs-risk-part-rows").getByRole("button", { name: /Fan retaining ring/ }).tap();
  await expect(page.locator(".rs-part-callout")).toHaveCount(1);
  await expect(page.locator(".rs-part-callout-label")).toHaveText("Fan retaining ring");
  const selectedStableId = await page.locator(".rs-part-callout").getAttribute("data-part-id");
  expect(selectedStableId).not.toBeNull();
  await expect.poll(() => anchorError(page, selectedStableId!)).toBeLessThan(2);
  await expect.poll(() => page.locator(".rs-part-callout-label").evaluate(el => {
    const b = el.getBoundingClientRect();
    return b.left >= 0 && b.right <= innerWidth && b.top >= 0 && b.bottom <= innerHeight;
  })).toBe(true);
  await page.screenshot({ path: info.outputPath("mobile-callout.png") });
  await page.locator(".rs-risk-panel").getByRole("button", { name: "Close part risk panel", exact: true }).tap();
  await expect(page.locator(".rs-part-callout, .rs-hotspot")).toHaveCount(0);
  await context.close();
});
