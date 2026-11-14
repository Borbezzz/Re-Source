import { test, expect } from "@playwright/test";
import { startSeededRun } from "./helpers";

test("source selections survive the initial engine connection", async ({
  page,
}) => {
  await startSeededRun(page);
  let releaseEngine!: () => void;
  const connection = new Promise<void>((resolve) => {
    releaseEngine = resolve;
  });
  await page.route("**/api/v1/engines/engine-demo-001", async (route) => {
    await connection;
    await route.continue();
  });
  await page.goto("/#sources");
  const inputs = page.locator("input[type=file]");
  await inputs.nth(0).setInputFiles({
    name: "blueprint.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Synthetic blueprint"),
  });
  await inputs.nth(1).setInputFiles({
    name: "requirements.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Synthetic requirements"),
  });
  const extract = page.getByRole("button", {
    name: "Extract & review requirements",
  });
  await expect(extract).toBeDisabled();
  releaseEngine();
  await expect(extract).toBeEnabled();
  await expect(page.locator(".file-button").nth(0)).toContainText(
    "blueprint.txt",
  );
  await expect(page.locator(".file-button").nth(1)).toContainText(
    "requirements.txt",
  );
  // An intentional new run must still discard selections from the old run.
  await page.getByRole("button", { name: "Demo data options" }).click();
  await page.getByRole("button", { name: "Start new session" }).click();
  await expect(page.locator(".file-button").nth(0)).toContainText(
    "Choose blueprint",
  );
  await expect(extract).toBeDisabled();
});

test("two sources, cited review, correction, confirmation and truthful generation blocker", async ({
  page,
}) => {
  await startSeededRun(page);
  await page.goto("/");
  await page
    .getByRole("button", { name: "Sources & requirements", exact: true })
    .click();
  await page
    .locator("input[type=file]")
    .nth(0)
    .setInputFiles({
      name: "illustrative-blueprint.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(
        "SYNTHETIC TEST BLUEPRINT\nRS-TF2 combustor component 7: fuel nozzle. This text is not accurate engineering geometry.",
      ),
    });
  await page
    .locator("input[type=file]")
    .nth(1)
    .setInputFiles({
      name: "test-part-requirements.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(
        "PART_NUMBER: RS-FN-1001\nREVISION: D\nDESCRIPTION: Synthetic test specification for fuel nozzle\nMATERIAL: Test alloy, illustrative only\nKEY_DIMENSIONS: 12 mm (synthetic test value)\nAPPLICABLE_STANDARDS: TEST-STANDARD\n",
      ),
    });
  const uploadedBlueprint = page.waitForResponse(
    (r) =>
      r.url().endsWith("/intake/uploads") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Extract & review requirements" })
    .click();
  const blueprintId = (await (await uploadedBlueprint).json()).upload_id;
  await expect(
    page.getByRole("heading", { name: "Review extracted fields" }),
  ).toBeVisible();
  await expect(page.getByLabel("Part number · required")).toHaveValue(
    "RS-FN-1001",
  );
  await expect(page.locator(".source-preview")).toContainText("RS-FN-1001");
  await page
    .getByLabel("Material", { exact: true })
    .fill("Revised synthetic test alloy");
  await expect(
    page.getByRole("button", { name: "Confirm requirements", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Save corrections" }).click();
  await expect(
    page.getByRole("button", { name: "Confirm requirements", exact: true }),
  ).toBeEnabled();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: ".impeccable/review/intake-review-desktop.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Confirm requirements", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Generate assembly", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "A mesh-generation provider is required.",
    }),
  ).toBeVisible();
  await expect(page.locator(".mesh-job")).toContainText(
    "No 3D mesh has been generated",
  );
  await page.reload();
  await expect(
    page.getByRole("heading", {
      name: "A mesh-generation provider is required.",
    }),
  ).toBeVisible();
  await expect(page.getByLabel("Material", { exact: true })).toHaveValue(
    "Revised synthetic test alloy",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: ".impeccable/review/intake-review-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page
    .locator("summary")
    .filter({ hasText: "Use an existing segmented GLB" })
    .click();
  await page.locator('input[accept=".glb"]').setInputFiles({
    name: "synthetic-test.glb",
    mimeType: "model/gltf-binary",
    buffer: testMesh(blueprintId),
  });
  const activate = page.getByRole("button", {
    name: "Activate validated assembly",
  });
  await expect(activate).toBeDisabled();
  await page
    .getByRole("checkbox", { name: /I checked every part identity/ })
    .check();
  await expect(activate).toBeEnabled();
  await activate.click();
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-ready",
    "true",
  );
  await expect(page.locator(".scene-root")).not.toContainText(
    "Model unavailable",
  );
  await page
    .getByRole("button", {
      name: "Select Combustor fuel nozzle (position 7)",
      exact: true,
    })
    .click();
  await expect(page.locator(".inspector h2")).toHaveText("Fuel nozzle");
  const uploadedPath = await page
    .locator(".scene-root")
    .getAttribute("data-asset");
  expect(uploadedPath).toMatch(/\/intake\/uploads\/.+\/content$/);
  await page.reload();
  // The source workflow intentionally resumes on its own route. Reopen the
  // assembly in the same visitor/run to check the persisted activated asset.
  await expect(
    page.getByRole("heading", { name: "Generate the assembly." }),
  ).toBeVisible();
  await page.goto("/#engine");
  await page.reload();
  await expect(page.locator(".intro-parts button").first()).toBeEnabled();
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-asset",
    uploadedPath!,
  );
  await expect(page.locator(".scene-root")).toHaveAttribute(
    "data-ready",
    "true",
  );
});

// Three explicitly synthetic triangles test binary loading + identity mapping.
// They are not generated engine geometry or engineering evidence.
function testMesh(uploadId: string): Buffer {
  const names = [
    "Component_FuelNozzle_07",
    "Component_NGV_Segment_12",
    "Component_BleedDuct_HP",
  ];
  const positions = [
    [0.05, 0.62, 0.18],
    [0.42, 0.48, -0.12],
    [-0.3, 0.7, 0.35],
  ];
  const binary = Buffer.alloc(3 * 36);
  const vertices = [-0.1, -0.1, -0.1, 0.1, 0.1, 0.1, -0.1, 0.1, -0.1];
  names.forEach((_, i) =>
    vertices.forEach((value, j) => binary.writeFloatLE(value, i * 36 + j * 4)),
  );
  const doc = {
    asset: { version: "2.0", generator: "synthetic integration test" },
    scene: 0,
    scenes: [{ nodes: [0, 1, 2] }],
    nodes: names.map((name, i) => ({
      name,
      mesh: i,
      translation: positions[i],
      extras: {
        source_ref: {
          upload_id: uploadId,
          page: 1,
          excerpt: `Synthetic blueprint item ${i + 1}`,
        },
      },
    })),
    meshes: names.map((_, i) => ({
      primitives: [{ attributes: { POSITION: i } }],
    })),
    accessors: names.map((_, i) => ({
      bufferView: i,
      componentType: 5126,
      count: 3,
      type: "VEC3",
      min: [-0.1, -0.1, -0.1],
      max: [0.1, 0.1, 0.1],
    })),
    bufferViews: names.map((_, i) => ({
      buffer: 0,
      byteOffset: i * 36,
      byteLength: 36,
    })),
    buffers: [{ byteLength: binary.length }],
  };
  let json = Buffer.from(JSON.stringify(doc));
  json = Buffer.concat([json, Buffer.alloc((4 - (json.length % 4)) % 4, 32)]);
  const header = Buffer.alloc(20);
  header.writeUInt32LE(0x46546c67, 0);
  header.writeUInt32LE(2, 4);
  header.writeUInt32LE(28 + json.length + binary.length, 8);
  header.writeUInt32LE(json.length, 12);
  header.writeUInt32LE(0x4e4f534a, 16);
  const binHeader = Buffer.alloc(8);
  binHeader.writeUInt32LE(binary.length, 0);
  binHeader.writeUInt32LE(0x004e4942, 4);
  return Buffer.concat([header, json, binHeader, binary]);
}
