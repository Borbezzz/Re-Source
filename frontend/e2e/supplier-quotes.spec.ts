import { expect, test } from "@playwright/test";
import { fileURLToPath } from "node:url";

test.use({
  channel: process.env.RESOURCE_BROWSER_CHANNEL || undefined,
  headless: !process.env.RESOURCE_HEADED,
});

const pdf = fileURLToPath(
  new URL("../../tests/fixtures/quotes/sample-quote.pdf", import.meta.url),
);
const reply = [
  "Hello, we can supply 4 units at EUR 142 each and dispatch in 12 working days.",
  "Part number: RS-DEMO-FB-001",
  "Revision: C",
  "Minimum order: 5 units",
  "Exceptions: inspection charged separately",
].join("\n");

test("opens supplier quotes from the Studio assembly and returns with Escape", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.goto("/");
  await page.locator('input[type="file"]').first().setInputFiles(fileURLToPath(new URL("../public/packages/mechanica-input-package.zip", import.meta.url)));
  await page.getByLabel("Delivery destination").fill("Bristol, UK");
  await page.getByLabel("Need-by date").fill("2026-11-24");
  await page.getByRole("button", { name: "Confirm parts and scan supply risk" }).click();
  const open = page.getByRole("button", { name: "Supplier quotes" });
  await open.click();
  const dialog = page.getByRole("dialog", { name: "Supplier quotes" });
  await expect(
    dialog.getByRole("heading", { name: "Supplier quotes" }),
  ).toBeVisible();
  await expect(
    dialog.getByRole("heading", { name: "Compare quotes" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(open).toBeFocused();
});

test("imports and compares a PDF and pasted reply, then reopens the saved review on mobile", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.emulateMedia({ reducedMotion: "reduce" });
  const projectResponse = await page.request.post("/api/v1/products", {
    data: { demo_id: "turbofan" },
  });
  expect(projectResponse.status()).toBe(201);
  const { project_id: projectId } = await projectResponse.json();
  await page.goto(`/#project/${projectId}`);
  await page.getByRole("link", { name: "Supplier quotes" }).click();
  const dialog = page.getByRole("main", { name: "Supplier quotes" });
  await dialog
    .getByLabel("Part", { exact: true })
    .selectOption("rs-tf-fan-blade");

  await dialog
    .getByLabel("Supplier", { exact: true })
    .fill("Northline Components");
  await dialog.locator('input[type="file"]').setInputFiles(pdf);
  await dialog
    .getByRole("button", { name: "Import quote", exact: true })
    .click();
  await expect(dialog.getByRole("cell", { name: "GBP 125.50" })).toBeVisible();

  await dialog.getByRole("radio", { name: "Paste reply" }).check();
  await dialog.getByLabel("Supplier", { exact: true }).fill("Westmoor Supply");
  await dialog.getByLabel("Supplier reply").fill(reply);
  await dialog
    .getByRole("button", { name: "Import quote", exact: true })
    .click();
  const table = dialog.getByRole("table", { name: /Supplier quotes for/ });
  await expect(table.getByRole("cell", { name: "EUR 142 each" })).toBeVisible();
  await expect(table.getByRole("row", { name: /Lead time/ })).toContainText(
    "12 working days",
  );
  await expect(table.getByRole("row", { name: /Lead time/ })).toContainText(
    "8 working days",
  );
  await expect(
    table.getByText("Revision differs. Requested B; offered C."),
  ).toBeVisible();
  await expect(
    table.getByRole("row", { name: /Certificates and documents/ }),
  ).toContainText("Not supplied");
  await page.screenshot({ path: info.outputPath("desktop.png") });

  await dialog.getByText("Review source · Northline Components").click();
  await expect(
    dialog.getByText("Page 2 · Lead time: 8 working days"),
  ).toBeVisible();
  await dialog.getByText("Review source · Westmoor Supply").click();
  const westmoor = dialog
    .locator(".rs-quote-evidence > details")
    .filter({ hasText: "Review source · Westmoor Supply" });
  await westmoor.getByText("Follow-up draft", { exact: true }).click();
  await expect(
    westmoor.locator("pre").filter({ hasText: "Revision differs" }),
  ).toBeVisible();
  await westmoor.getByRole("button", { name: "Review terms" }).click();
  await westmoor.getByLabel("Revision", { exact: true }).fill("B");
  await westmoor.getByRole("button", { name: "Save review" }).click();
  await expect(
    table.getByText("Revision differs. Requested B; offered C."),
  ).toHaveCount(0);
  await expect(westmoor.getByText("Revision · Buyer edit")).toBeVisible();

  const source = await westmoor
    .getByRole("link", { name: "Supplier reply.txt" })
    .getAttribute("href");
  const downloadedReply = await (await page.request.get(source!)).text();
  expect(downloadedReply.replaceAll("\r\n", "\n")).toBe(reply);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("link", { name: "Back to investigation" }).click();
  await page.getByRole("link", { name: "Supplier quotes" }).click();
  await expect(
    page.getByRole("heading", { name: "Supplier quotes" }),
  ).toBeVisible();
  await expect(
    page.getByRole("columnheader", { name: /Westmoor Supply Reviewed/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("columnheader", {
      name: /Northline Components Needs review/,
    }),
  ).toBeVisible();
  await page.reload();
  await expect(page.getByRole("cell", { name: "EUR 142 each" })).toBeVisible();
  const fits = await page
    .locator(".rs-quote-page")
    .evaluate((workspace) => workspace.scrollWidth <= workspace.clientWidth);
  expect(fits).toBe(true);
  await page
    .getByRole("heading", { name: "Compare quotes" })
    .scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("mobile.png") });
  expect(errors).toEqual([]);
});
