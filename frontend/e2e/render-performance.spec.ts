import { test, expect } from "@playwright/test";
import { fileURLToPath } from "node:url";

test.use({ channel: process.env.RESOURCE_BROWSER_CHANNEL || undefined });
const archive = fileURLToPath(new URL("../../blueprint input/mechanica-input-package.zip", import.meta.url));

test("full-detail assembly sleeps at rest and wakes for controls and the complete reassembly journey", async ({ page }, info) => {
  test.setTimeout(120_000);
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  await page.addInitScript(() => {
    const observedRoots = new Set<string>();
    let scene: any;
    Object.defineProperty(window, "__rsScene", {
      configurable: true,
      get: () => scene,
      set: value => {
        scene = value;
        observedRoots.add(value.prepared.root.uuid);
        (window as any).__rsPreparedRoots = [...observedRoots];
      },
    });
  });
  await page.goto("/");
  await page.locator('input[type="file"]').first().setInputFiles(archive);
  const confirm = page.getByRole("button", { name: "Confirm and open assembly", exact: true });
  await expect(confirm).toBeEnabled();
  const scan = await page.evaluate(() => {
    const { gl, prepared: p } = (window as any).__rsScene;
    return { calls: gl.info.render.calls, meshes: p.meshes.length,
      scanInstances: p.scanRoot.children.reduce((sum: number, m: any) => sum + m.geometry.instanceCount, 0) };
  });
  expect(scan.calls).toBeGreaterThan(0);
  expect(scan.calls).toBeLessThan(scan.meshes / 4);
  expect(scan.scanInstances).toBe(scan.meshes);
  expect(await page.evaluate(() => (window as any).__rsPreparedRoots.length)).toBe(1);
  await confirm.click();
  await expect(page.getByRole("complementary", { name: "Assembly parts" })).toBeVisible();
  const frames = () => page.evaluate(() => (window as any).__rsScene.gl.info.render.frame);
  await expect.poll(async () => {
    const before = await frames();
    await page.waitForTimeout(500);
    return await frames() - before;
  }, { timeout: 15_000 }).toBe(0);
  await page.getByRole("button", { name: "Rotate", exact: true }).click();
  const beforeRotation = await frames();
  await expect.poll(frames).toBeGreaterThan(beforeRotation + 5);
  await page.getByRole("button", { name: "Rotate", exact: true }).click();
  const casingOffset = () => page.evaluate(() => {
    const g = (window as any).__rsScene.prepared.groups.get("casing");
    return g.node.position.y - g.home.y;
  });
  await page.getByRole("button", { name: "Explode", exact: true }).click();
  await expect.poll(casingOffset).toBeGreaterThan(3.3);
  await page.getByRole("button", { name: "Assemble", exact: true }).click();
  await expect.poll(casingOffset).toBeLessThan(0.001);

  await page.getByRole("button", { name: /^Fan blades 24/ }).click();
  await page.getByRole("button", { name: /^Change supplier/ }).click();
  await page.evaluate(() => {
    const gl = (window as any).__rsScene.gl;
    const setSize = gl.setSize.bind(gl);
    (window as any).__rsHiddenResizes = [];
    gl.setSize = (...args: any[]) => {
      if (document.querySelector('.rs-scene-layer[aria-hidden="true"]')) (window as any).__rsHiddenResizes.push(args.slice(0, 2));
      return setSize(...args);
    };
  });
  await page.getByRole("button", { name: "Find suppliers", exact: true }).click();
  await page.getByRole("button", { name: "Show all results", exact: true }).click();
  await page.getByRole("button", { name: "Compare shortlist", exact: true }).click();
  expect(await page.evaluate(() => (window as any).__rsHiddenResizes)).toEqual([]);
  await page.getByRole("button", { name: "Workflow", exact: true }).click();
  await expect(page.locator(".fl-pane.is-full")).toBeVisible();
  await page.locator(".fl-pane.is-full").getByRole("button", { name: "Scene", exact: true }).click();
  await page.getByRole("button", { name: "Select supplier", exact: true }).click();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Approve enquiry", exact: true }).click();
  await page.getByRole("button", { name: "Send enquiry (simulated)", exact: true }).click();
  await page.getByRole("button", { name: "Preview reassembly", exact: true }).click();
  const partOffset = () => page.evaluate(() => {
    const p = (window as any).__rsScene.prepared;
    return Math.max(...p.compNodes.get("RS-TF-FAN-BLADE").map((n: any) => n.position.distanceTo(p.nodeHome.get(n.userData.stableId))));
  });
  await expect.poll(partOffset, { intervals: [100] }).toBeGreaterThan(0.2);
  await expect(page.getByText("Replacement matched", { exact: true })).toBeVisible();
  await expect.poll(partOffset).toBeLessThan(0.001);
  await page.screenshot({ path: info.outputPath("reassembly.png") });
  await page.getByRole("button", { name: "Back to assembly", exact: true }).click();
  await expect(page.getByRole("complementary", { name: "Assembly parts" })).toBeVisible();
  expect(errors).toEqual([]);
});
