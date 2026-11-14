import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { startSeededRun } from "./helpers";

test("premade engine persists across API resolution, existing run reload and all three case selections", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await startSeededRun(page);
  const getEngine = async () => {
    const r = await page.request.get("/api/v1/engines/engine-demo-001");
    expect(r.ok()).toBeTruthy();
    return r.json();
  };
  const before = await getEngine();
  await page.goto("/#engine");
  await expect(page.locator(".intro-parts button").first()).toBeEnabled();
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-asset",
    "/models/engine-cutaway.glb",
  );
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-ready",
    "true",
  );
  await page.reload();
  await expect(page.locator(".intro-parts button").first()).toBeEnabled();
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-asset",
    "/models/engine-cutaway.glb",
  );
  await page.locator(".intro-parts button").first().click();
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-ready",
    "true",
  );
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-asset",
    "/models/engine-cutaway.glb",
  );
  for (let i = 0; i < 3; i++) {
    await page.locator(".mesh-pin").nth(i).click();
    await expect(page.locator(".mesh-pin").nth(i)).toHaveClass(/active/);
  }
  for (const width of [1440, 720]) {
    await page.setViewportSize({ width, height: 900 });
    if (width === 720) {
      await expect
        .poll(async () =>
          page
            .locator(".mesh-overlay line")
            .nth(2)
            .evaluate((line) => {
              const host = line.closest(".scene-root")!.getBoundingClientRect();
              return (
                Math.abs(Number(line.getAttribute("x1")) - host.width / 2) <
                  8 &&
                Math.abs(Number(line.getAttribute("y1")) - host.height / 2) < 8
              );
            }),
        )
        .toBe(true);
    }
    for (const separation of [0, 1]) {
      await page
        .getByRole("button", {
          name: separation ? "Explode" : "Assemble",
          exact: true,
        })
        .click();
      await expect(page.locator(".scene-root")).toHaveAttribute(
        "data-settled",
        "true",
      );
      for (let i = 0; i < 3; i++) {
        await page.locator(".mesh-pin").nth(i).click();
        await page
          .getByRole("button", { name: "Focus selected component" })
          .click();
        await expect
          .poll(async () =>
            page
              .locator(".mesh-overlay line")
              .nth(i)
              .evaluate((line) => {
                const host = line
                  .closest(".scene-root")!
                  .getBoundingClientRect();
                const x = Number(line.getAttribute("x1")),
                  y = Number(line.getAttribute("y1"));
                return (
                  Math.abs(x - host.width / 2) < 8 &&
                  Math.abs(y - host.height / 2) < 8
                );
              }),
          )
          .toBe(true);
      }
    }
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.getByRole("button", { name: "Assemble", exact: true }).click();
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-settled",
    "true",
  );
  await mkdir(".impeccable/review/premade-engine", { recursive: true });
  await page.screenshot({
    path: ".impeccable/review/premade-engine/workspace.png",
  });
  const after = await getEngine();
  expect(after.scenario_run_id).toBe(before.scenario_run_id);
  expect(
    after.components.map((c: any) => [
      c.component_id,
      c.case_id,
      c.requirement_set_id,
      c.mesh_mapping.node_name,
    ]),
  ).toEqual(
    before.components.map((c: any) => [
      c.component_id,
      c.case_id,
      c.requirement_set_id,
      c.mesh_mapping.node_name,
    ]),
  );
  await page.reload();
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-asset",
    "/models/engine-cutaway.glb",
  );
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-ready",
    "true",
  );
  expect((await getEngine()).scenario_run_id).toBe(before.scenario_run_id);
  // Reopen an existing case after reload, without creating/replacing its run.
  if (await page.locator(".intro-parts").count())
    await page.locator(".intro-parts button").first().click();
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-asset",
    "/models/engine-cutaway.glb",
  );
  expect((await getEngine()).scenario_run_id).toBe(before.scenario_run_id);
  expect(errors).toEqual([]);
});
