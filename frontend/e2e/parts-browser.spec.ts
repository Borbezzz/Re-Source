import { test, expect } from "@playwright/test";
import { fileURLToPath } from "node:url";

test.use({ channel: process.env.RESOURCE_BROWSER_CHANNEL || undefined, headless: !process.env.RESOURCE_HEADED });
const archive = fileURLToPath(new URL("../../blueprint input/mechanica-input-package.zip", import.meta.url));

test("group and individual preview, keyboard selection, new-stage sourcing and widening supplier map", async ({ page }, info) => {
  test.setTimeout(150_000);
  await page.emulateMedia({ reducedMotion: "reduce" });
  const errors: string[] = [];
  const mutations: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("request", request => { if (request.url().includes("/api/") && request.method() !== "GET") mutations.push(request.url()); });
  await page.goto("/");
  await page.locator('input[type="file"]').first().setInputFiles(archive);
  await page.getByRole("button", { name: "Confirm and open assembly", exact: true }).click();
  await expect(page.getByRole("complementary", { name: "Assembly parts" })).toBeVisible();
  const hoverIds = () => page.evaluate(() => {
    const p = (window as any).__rsScene.prepared;
    return p.meshes.filter((m: any) => m.visible && m.material === p.hover).map((m: any) => m.userData.stableId);
  });
  const calls = mutations.length;
  await page.getByRole("button", { name: /^Fan blades 24/ }).hover();
  await expect.poll(async () => (await hoverIds()).length).toBe(24);
  await page.waitForTimeout(350); // allow the GPU frame to display the material change
  await page.screenshot({ path: info.outputPath("fan-group.png") });
  await page.getByRole("button", { name: "Expand Fan blades", exact: true }).click();
  await page.getByRole("button", { name: /^Fan blade 07/ }).hover();
  await expect.poll(hoverIds).toEqual(["rs-mech-tf-v1.fan.m000.i006"]);
  await page.waitForTimeout(350);
  await page.screenshot({ path: info.outputPath("blade-07.png") });
  await page.getByRole("button", { name: /^Fan blade 08/ }).focus();
  await expect.poll(hoverIds).toEqual(["rs-mech-tf-v1.fan.m000.i007"]);
  await page.keyboard.press("Escape");
  await page.mouse.move(12, 80);
  await expect.poll(hoverIds).toEqual([]);
  expect(mutations.length).toBe(calls);
  await page.getByRole("button", { name: /^Fan blade 07/ }).click();
  await expect(page.getByRole("region", { name: "Fan blade 07 actions" })).toBeVisible();
  expect(await page.evaluate(() => {
    const p = (window as any).__rsScene.prepared;
    return p.meshes.filter((m: any) => m.visible && m.material === p.highlight).map((m: any) => m.userData.stableId);
  })).toEqual(["rs-mech-tf-v1.fan.m000.i006"]);
  await page.getByRole("button", { name: "Clear selection", exact: true }).click();
  await expect(page.getByRole("region", { name: "Fan blade 07 actions" })).toBeHidden();
  await page.getByRole("button", { name: "Collapse Fan blades", exact: true }).click();
  await page.getByRole("button", { name: "Expand Axial compressor", exact: true }).click();
  const compressor = page.locator('[data-part-id="rs-mech-tf-v1.group.compressor"]');
  await compressor.getByRole("button", { name: "Expand Rotor blades", exact: true }).click();
  await compressor.getByRole("button", { name: /^Stage 3 40/ }).click();
  const card = page.getByRole("region", { name: "Compressor stage 3 rotor blades actions" });
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: /^Change supplier/ }).click();
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.getByRole("button", { name: "Find suppliers", exact: true }).click();
  await expect(page.locator(".rs-map")).toBeVisible();
  const initialWidth = Number((await page.locator(".rs-map-base").getAttribute("viewBox"))!.split(" ")[2]);
  const frames = await page.evaluate(() => new Promise<{ count: number; width: number }[]>(resolve => {
    const samples: { count: number; width: number }[] = [];
    const start = performance.now();
    const timer = setInterval(() => {
      const el = document.querySelector<HTMLElement>(".rs-map");
      const svg = el?.querySelector("svg");
      if (el && svg) samples.push({ count: Number(el.dataset.visibleSuppliers), width: Number(svg.getAttribute("viewBox")!.split(" ")[2]) });
      if (performance.now() - start > 6500) { clearInterval(timer); resolve(samples); }
    }, 80);
  }));
  await expect(page.locator(".rs-map [data-pin]")).toHaveCount(8);
  const early = frames.find(frame => frame.count > 0 && frame.count < 6)!;
  expect(early).toBeTruthy();
  // The camera zooms out once as the batch arrives, independently of pin reveals.
  expect(frames.at(-1)!.width).toBeGreaterThan(initialWidth * 2);
  await page.screenshot({ path: info.outputPath("supplier-map.png") });
  await info.attach("map-framing", { body: JSON.stringify(frames), contentType: "application/json" });
  await expect(page.getByText("Demo sourcing agent", { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test("mobile touch can expand the browser and select an individual blade without overflow", async ({ browser }, info) => {
  test.setTimeout(90_000);
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: "reduce" });
  const page = await context.newPage();
  await page.goto(process.env.RESOURCE_BASE_URL || "http://127.0.0.1:5173");
  await page.locator('input[type="file"]').first().setInputFiles(archive);
  await page.getByRole("button", { name: "Confirm and open assembly", exact: true }).tap();
  await page.getByRole("button", { name: "Expand Fan blades", exact: true }).tap();
  await page.getByRole("button", { name: /^Fan blade 03/ }).tap();
  await expect(page.getByRole("region", { name: "Fan blade 03 actions" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Fan blade 03 actions" })).toHaveCSS("opacity", "1");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath("mobile-selection.png") });
  await page.getByRole("button", { name: "Clear selection", exact: true }).tap();
  await expect(page.getByRole("complementary", { name: "Assembly parts" })).toBeVisible();
  await context.close();
});
