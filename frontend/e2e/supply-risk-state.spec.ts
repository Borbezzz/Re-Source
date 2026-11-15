import { test, expect as baseExpect, type APIResponse } from "@playwright/test";
import type { ProductProject } from "../src/product-flow/types";

const expect = baseExpect.configure({ timeout: 20_000 });

async function projectResponse(response: APIResponse): Promise<ProductProject> {
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json();
}

test("unstarted needs retain their snapshot on focus, reject stale submission and recover on reopen", async ({ page }) => {
  test.setTimeout(120_000);
  await page.emulateMedia({ reducedMotion: "reduce" });
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));

  const original = await projectResponse(await page.request.post("/api/v1/products", {
    data: { demo_id: "turbofan" },
  }));
  const projectPath = `/api/v1/products/${original.project_id}`;
  const riskPath = `${projectPath}/supply-risk`;
  const responseFor = (path: string, method = "GET") =>
    page.waitForResponse(response =>
      new URL(response.url()).pathname === path && response.request().method() === method
    );

  const initialProject = responseFor(projectPath);
  const initialScan = responseFor(riskPath);
  await page.goto(`/#risk/${original.project_id}`);
  expect((await initialProject).ok()).toBeTruthy();
  expect((await (await initialScan).json()).status).toBe("not_started");

  const form = page.locator(".rs-risk-needs");
  const identity = form.getByLabel("Part number", { exact: true }).first();
  await expect(identity).toHaveValue(original.parts[0].part_number ?? "");
  await identity.fill("LOCAL-DRAFT-PN");
  await form.getByLabel("Revision", { exact: true }).first().fill("LOCAL-REV");
  await form.getByLabel("Delivery destination").fill("Bristol, UK");
  await form.getByLabel("Need-by date").fill("2026-11-24");
  const mountedForm = await form.elementHandle();
  expect(mountedForm).not.toBeNull();

  const newer = await projectResponse(await page.request.patch(`${projectPath}/parts`, {
    data: {
      expected_version: original.version,
      confirm: true,
      parts: original.parts.map((part, index) => ({
        ...part,
        status: "confirmed",
        ...(index === 0 ? {
          part_number: "CONCURRENT-PN",
          part_number_source: null,
          quantity: part.quantity + 3,
          quantity_source: null,
        } : {}),
        requirements: part.requirements.map(requirement => ({
          ...requirement,
          status: "confirmed",
          ...(index === 0 && requirement.key === "part_number"
            ? { value: "CONCURRENT-PN", source: null }
            : {}),
        })),
      })),
    },
  }));
  expect(newer.version).toBeGreaterThan(original.version);

  const focusedProject = responseFor(projectPath);
  const focusedScan = responseFor(riskPath);
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  const loadedProject = await focusedProject;
  expect(loadedProject.ok()).toBeTruthy();
  expect((await loadedProject.json()).version).toBe(newer.version);
  expect((await focusedScan).ok()).toBeTruthy();
  await loadedProject.finished();
  // Let the response-driven React render commit; no elapsed-time sleep.
  await page.evaluate(() => new Promise<void>(resolve =>
    requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
  ));

  expect(await mountedForm!.evaluate(el =>
    el.isConnected && el === document.querySelector(".rs-risk-needs")
  )).toBe(true);
  await expect(identity).toHaveValue("LOCAL-DRAFT-PN");
  await expect(form.getByLabel("Revision", { exact: true }).first()).toHaveValue("LOCAL-REV");
  await expect(form.getByLabel("Delivery destination")).toHaveValue("Bristol, UK");
  await expect(form.getByLabel("Need-by date")).toHaveValue("2026-11-24");

  const rejected = responseFor(`${projectPath}/parts`, "PATCH");
  await form.getByRole("button", { name: "Confirm parts and scan supply risk", exact: true }).click();
  const conflict = await rejected;
  expect(conflict.request().postDataJSON().expected_version).toBe(original.version);
  expect(conflict.request().postDataJSON().parts[0].part_number).toBe("LOCAL-DRAFT-PN");
  expect(conflict.status()).toBe(409);
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(identity).toHaveValue("LOCAL-DRAFT-PN");
  const unchanged = await projectResponse(await page.request.get(projectPath));
  expect(unchanged.version).toBe(newer.version);
  expect(unchanged.parts).toEqual(newer.parts);

  // The initial unstarted form intentionally has no Back to scan control.
  // Reopening the saved page is the available way to discard this stale draft.
  const reopenedProject = responseFor(projectPath);
  const reopenedScan = responseFor(riskPath);
  await page.reload();
  expect((await reopenedProject).ok()).toBeTruthy();
  expect((await reopenedScan).ok()).toBeTruthy();
  await expect(identity).toHaveValue("CONCURRENT-PN");
  await expect(form.getByLabel("Purchase quantity").first()).toHaveValue(String(newer.parts[0].quantity));
  await form.getByLabel("Delivery destination").fill("Bristol, UK");
  await form.getByLabel("Need-by date").fill("2026-11-24");
  const recovered = responseFor(`${riskPath}/confirm`, "POST");
  const refreshed = responseFor(`${riskPath}/refresh`, "POST");
  await form.getByRole("button", { name: "Confirm parts and scan supply risk", exact: true }).click();
  const recovery = await recovered;
  expect(recovery.ok()).toBeTruthy();
  expect(recovery.request().postDataJSON().expected_project_version).toBe(newer.version);
  expect((await refreshed).ok()).toBeTruthy();
  await expect(form).toHaveCount(0);

  // Evidence updates can advance project state without replacing RiskPage's
  // cached project. Opening needs must fetch a fresh snapshot before editing.
  await page.locator(".rs-risk-part-rows button").first().click();
  const panel = page.locator(".rs-risk-panel");
  await panel.getByRole("button", { name: "Add evidence", exact: true }).click();
  const evidence = panel.locator(".rs-risk-evidence-form");
  await evidence.getByLabel("Document title").fill("Snapshot regression quote");
  await evidence.getByLabel("Source date", { exact: true }).fill("2026-11-04");
  await evidence.getByLabel("Source excerpt").fill("Supplier A quotes arrival in Bristol, UK on 22 November.");
  await evidence.getByLabel("Supplier", { exact: true }).fill("Supplier A");
  await evidence.getByLabel("Arrival / receipt date").fill("2026-11-22");
  await evidence.getByLabel("I checked these fields").check();
  const savedEvidence = responseFor(`${riskPath}/evidence`, "POST");
  await evidence.getByRole("button", { name: "Save evidence and reassess", exact: true }).click();
  expect((await savedEvidence).ok()).toBeTruthy();
  await expect(evidence).toHaveCount(0);

  const editProject = responseFor(projectPath);
  await page.getByRole("region", { name: "Supply-risk scan", exact: true })
    .getByRole("button", { name: "Edit project needs", exact: true }).click();
  const editResponse = await editProject;
  expect(editResponse.ok()).toBeTruthy();
  const editSnapshot: ProductProject = await editResponse.json();
  await expect(identity).toHaveValue(editSnapshot.parts[0].part_number ?? "");
  await identity.fill("AFTER-EVIDENCE-PN");
  const editedParts = responseFor(`${projectPath}/parts`, "PATCH");
  const editedScan = responseFor(`${riskPath}/confirm`, "POST");
  await form.getByRole("button", { name: "Confirm parts and scan supply risk", exact: true }).click();
  const edit = await editedParts;
  expect(edit.request().postDataJSON().expected_version).toBe(editSnapshot.version);
  expect(edit.ok()).toBeTruthy();
  expect((await editedScan).ok()).toBeTruthy();
  await expect(form).toHaveCount(0);
  expect(errors).toEqual([]);
});
