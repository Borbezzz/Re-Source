import { test } from "node:test";
import assert from "node:assert/strict";
import { workflowProviders, type ProviderProject } from "../src/studio/flow/providers.ts";
import type { ProductInvestigation } from "../src/product-flow/types.ts";

function project(research: Partial<ProductInvestigation> = {}): ProviderProject {
  return {
    capabilities: {
      storage: "lakebase_postgres", execution: "durable_queue",
      document_parsing: "databricks_configured", requirement_extraction: "structured_documents_only",
      supplier_discovery: "linkup_configured", model_generation: "provider_required",
    },
    documents: [{ document_id: "bom", name: "parts.json", kind: "requirements", data_origin: "synthetic_demo", media_type: "application/json", size_bytes: 200, extraction_status: "complete", extraction_method: "prepared_demo" }],
    research: [{ part_id: "fan", job_id: "job", mode: "demo", status: "complete", stage: "complete", providers_used: ["prepared_demo"], candidates: [], ...research }],
  };
}

test("configured integrations do not turn a prepared demo into provider calls", () => {
  const p = workflowProviders(project(), "fan");
  assert.equal(p.searchStatus, "skipped");
  assert.equal(p.extractStatus, "skipped");
  assert.equal(p.linkupUsed, false);
  assert.match(p.storage, /Databricks Lakebase/);
  assert.equal(p.execution, "Vercel Queues");
  assert.match(p.parsing, /Not run · prepared package/);
});

test("only recorded provider successes are shown as complete", () => {
  const p = workflowProviders(project({ mode: "live", providers_used: ["linkup", "databricks_ai_extract"] }), "fan");
  assert.equal(p.searchStatus, "done");
  assert.equal(p.extractStatus, "done");
  const fallback = workflowProviders(project({ mode: "live", providers_used: ["linkup"] }), "fan");
  assert.equal(fallback.searchStatus, "done");
  assert.equal(fallback.extractStatus, "skipped");
  assert.equal(fallback.extractSummary, "Source snippets retained");
});

test("active phases and failed calls never imply a successful provider result", () => {
  const search = workflowProviders(project({ mode: "live", status: "running", stage: "searching", providers_used: [] }), "fan");
  assert.equal(search.searchStatus, "running");
  assert.equal(search.extractStatus, "idle");
  const extract = workflowProviders(project({ mode: "live", status: "running", stage: "databricks", providers_used: [] }), "fan");
  assert.equal(extract.extractStatus, "running");
  assert.notEqual(extract.searchStatus, "done");
  const failed = workflowProviders(project({ mode: "live", status: "failed", providers_used: [] }), "fan");
  assert.equal(failed.searchStatus, "error");
  assert.equal(failed.extractStatus, "skipped");
});

test("local persistence and document parser provenance come from the current project", () => {
  const local = project();
  local.capabilities.storage = "local_sqlite";
  local.capabilities.execution = "local_worker";
  local.documents[0].extraction_method = "pdf_text";
  let p = workflowProviders(local, "fan");
  assert.equal(p.storage, "Local SQLite");
  assert.match(p.parsing, /Not run/);
  local.documents[0].extraction_method = "databricks_ai_parse_document";
  p = workflowProviders(local, "fan");
  assert.equal(p.parsing, "Used on 1 document: parts.json");
});

test("another part's completed investigation cannot supply provenance for this part", () => {
  const p = workflowProviders(project({ mode: "live", providers_used: ["linkup", "databricks_ai_extract"] }), "other-part");
  assert.equal(p.linkupUsed, false);
  assert.equal(p.extractStatus, "skipped");
  assert.equal(workflowProviders().storage, "Storage not reported");
});
