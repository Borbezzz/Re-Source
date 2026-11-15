import { test, expect, type Page } from "@playwright/test";
import { fileURLToPath } from "node:url";

test.use({ channel: process.env.RESOURCE_BROWSER_CHANNEL || undefined });
const archive = fileURLToPath(new URL("../../blueprint input/mechanica-input-package.zip", import.meta.url));

async function settle(page: Page) {
  await expect.poll(async () => {
    const frame = await page.evaluate(() => (window as any).__rsScene.gl.info.render.frame);
    await page.waitForTimeout(300);
    return page.evaluate(before => (window as any).__rsScene.gl.info.render.frame - before, frame);
  }, { timeout: 20_000 }).toBe(0);
}

test("full housing, cut-through picking and a separated, framed exploded housing", async ({ page }, info) => {
  test.setTimeout(120_000);
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/");
  await page.locator('input[type="file"]').first().setInputFiles(archive);
  await page.getByRole("button", { name: "Confirm and open assembly", exact: true }).click();
  const cut = page.getByRole("button", { name: "Cut through", exact: true });
  await expect(cut).toHaveAttribute("aria-pressed", "false");
  await settle(page);
  expect(await page.evaluate(() => (window as any).__rsScene.prepared.mats.casing.clippingPlanes)).toBeNull();
  await page.screenshot({ path: info.outputPath("full-housing.png") });

  await cut.click();
  await expect(cut).toHaveAttribute("aria-pressed", "true");
  await settle(page);
  await page.screenshot({ path: info.outputPath("cut-through.png") });
  // Find a real exposed surface whose click was previously blocked by invisible casing.
  const target = await page.evaluate(async () => {
    const threeUrl = "/node_modules/three/build/three.module.js";
    const T = await import(/* @vite-ignore */ threeUrl);
    const { prepared: p, camera } = (window as any).__rsScene;
    const rect = document.querySelector(".rs-scene-layer canvas")!.getBoundingClientRect();
    const ray = new T.Raycaster();
    const source = (hit: any) => hit?.instanceId == null ? hit?.object.userData.source : hit.object.userData.sources[hit.instanceId];
    for (const mesh of p.meshes.filter((m: any) => ["compressor", "combustor", "turbine"].includes(m.userData.group))) {
      mesh.geometry.computeBoundingSphere();
      const projected = mesh.geometry.boundingSphere.center.clone().applyMatrix4(mesh.matrixWorld).project(camera);
      const x = rect.x + (projected.x + 1) * rect.width / 2;
      const y = rect.y + (1 - projected.y) * rect.height / 2;
      if (document.elementFromPoint(x, y)?.tagName !== "CANVAS") continue;
      ray.setFromCamera(new T.Vector2(projected.x, projected.y), camera);
      const before = ray.intersectObjects(p.meshes, false)[0];
      const after = ray.intersectObject(p.instances.root, true)[0];
      const hitSource = source(after);
      if (before?.object.userData.group !== "casing" || !hitSource || hitSource.userData.group === "casing") continue;
      const planes = before.object.material.clippingPlanes;
      if (!planes?.every((plane: any) => plane.distanceToPoint(before.point) < 0)) continue;
      return { x, y, id: hitSource.userData.attachedToStableId ?? hitSource.userData.stableId,
        blockedBy: before.object.userData.stableId, group: hitSource.userData.group };
    }
    return null;
  });
  expect(target).not.toBeNull();
  await info.attach("direct-click-target", { body: JSON.stringify(target), contentType: "application/json" });
  await page.mouse.click(target!.x, target!.y);
  await expect(page.locator(".rs-part-callout")).toHaveAttribute("data-part-id", target!.id, { timeout: 5_000 });
  await page.getByRole("button", { name: "Clear selection", exact: true }).click();
  await settle(page);
  await cut.click();
  await expect(cut).toHaveAttribute("aria-pressed", "false");
  await settle(page);
  // The same pixel now selects the restored housing, proving the toggle works both ways.
  await page.mouse.click(target!.x, target!.y);
  await expect(page.locator(".rs-part-callout")).toHaveAttribute("data-part-id", target!.blockedBy);
  await page.getByRole("button", { name: "Clear selection", exact: true }).click();
  await page.getByRole("button", { name: "Explode", exact: true }).click();
  await settle(page);
  const exploded = await page.evaluate(async () => {
    const threeUrl = "/node_modules/three/build/three.module.js";
    const T = await import(/* @vite-ignore */ threeUrl);
    const { prepared: p, camera } = (window as any).__rsScene;
    const casing = new T.Box3().setFromObject(p.groups.get("casing").node);
    const internals = new T.Box3();
    for (const [id, { node }] of p.groups) if (id !== "casing") internals.expandByObject(node);
    const corners = [];
    for (const x of [casing.min.x, casing.max.x]) for (const y of [casing.min.y, casing.max.y]) for (const z of [casing.min.z, casing.max.z]) {
      const corner = new T.Vector3(x, y, z).project(camera);
      corners.push([corner.x, corner.y]);
    }
    return { clearance: casing.min.y - internals.max.y, corners };
  });
  expect(exploded.clearance).toBeGreaterThan(0.5);
  for (const [x, y] of exploded.corners) {
    expect(x).toBeGreaterThan(-1); expect(x).toBeLessThan(1);
    expect(y).toBeGreaterThan(-1); expect(y).toBeLessThan(1);
  }
  await page.screenshot({ path: info.outputPath("exploded-housing.png") });
  await cut.click();
  await expect(cut).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Reset view", exact: true }).click();
  await expect(cut).toHaveAttribute("aria-pressed", "false");
  await expect(page.getByRole("button", { name: "Explode", exact: true })).toHaveAttribute("aria-pressed", "false");
  await settle(page);
  await page.mouse.move(target!.x, target!.y);
  await page.mouse.down();
  await page.mouse.move(target!.x + 70, target!.y + 20, { steps: 8 });
  await page.mouse.up();
  await expect(page.locator(".rs-part-callout")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("cut-through and explode controls fit on mobile", async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.locator('input[type="file"]').first().setInputFiles(archive);
  await page.getByRole("button", { name: "Confirm and open assembly", exact: true }).click();
  const controls = page.locator(".rs-scene-controls");
  await expect(controls).toBeVisible();
  for (const button of await controls.getByRole("button").all()) {
    const box = (await button.boundingBox())!;
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(390);
  }
  await page.getByRole("button", { name: "Cut through", exact: true }).click();
  await expect(page.getByRole("button", { name: "Cut through", exact: true })).toHaveAttribute("aria-pressed", "true");
  await settle(page);
  await page.screenshot({ path: info.outputPath("mobile-cut-through.png") });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
