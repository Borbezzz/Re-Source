import type { ProductProject } from "../../product-flow/types.ts";

export type ProviderProject = Pick<ProductProject, "capabilities" | "research" | "documents">;

/** Configuration is not evidence that a provider ran. Use the recorded result. */
export function workflowProviders(project?: ProviderProject | null, partId?: string | null) {
  const research = project?.research.find((r) => r.part_id === partId);
  const used = new Set(research?.providers_used ?? []);
  const demo = research?.mode === "demo" || used.has("prepared_demo") || !research;
  const terminal = research?.status === "complete" || research?.status === "failed";
  const searching = !demo && research?.status === "running" && research.stage === "searching";
  const extracting = !demo && research?.status === "running" && research.stage === "databricks";
  const storage = project?.capabilities.storage === "lakebase_postgres"
    ? "Databricks Lakebase · Postgres"
    : project?.capabilities.storage === "local_sqlite" ? "Local SQLite" : "Storage not reported";
  const parsed = project?.documents.filter((d) => d.extraction_method === "databricks_ai_parse_document") ?? [];
  const prepared = project?.documents.some((d) => d.extraction_method === "prepared_demo");
  return {
    demo, research, storage,
    lakebase: project?.capabilities.storage === "lakebase_postgres",
    parsing: parsed.length
      ? `Used on ${parsed.length} document${parsed.length === 1 ? "" : "s"}: ${parsed.map((d) => d.name).join(", ")}`
      : prepared ? "Not run · prepared package already contains the parts and model"
        : "Not run · no document records this extraction method",
    linkupUsed: !demo && used.has("linkup"),
    searchStatus: demo ? "skipped" as const : used.has("linkup") ? "done" as const
      : research?.status === "failed" ? "error" as const : searching ? "running" as const
        : terminal ? "skipped" as const : "idle" as const,
    searchSummary: demo ? "Supplier catalogue offers" : used.has("linkup") ? "Cited supplier pages returned"
      : research?.status === "failed" ? "Search did not complete" : searching ? "Searching public sources…"
        : terminal ? "No successful call recorded" : "Waiting for supplier search",
    extractStatus: demo ? "skipped" as const : used.has("databricks_ai_extract") ? "done" as const
      : extracting ? "running" as const : terminal ? "skipped" as const : "idle" as const,
    extractSummary: demo ? "Catalogue supplier claims" : used.has("databricks_ai_extract") ? "Supplier claims extracted"
      : extracting ? "Extracting source claims…" : terminal ? "Source snippets retained"
        : "Waiting for cited sources",
    execution: project?.capabilities.execution === "durable_queue" ? "Vercel Queues" : project?.capabilities.execution === "local_worker" ? "Local worker" : "Not reported",
  };
}
