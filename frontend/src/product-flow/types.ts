/** Product workflow wire types; mirrors recovery.domain.products. */
export interface ProductSource {
  document_id: string;
  quote: string;
  page?: number | null;
}
export interface ProductRequirement {
  key: string;
  label: string;
  value: string;
  unit?: string | null;
  source?: ProductSource | null;
  status: "proposed" | "confirmed";
}
export interface ProductPart {
  part_id: string;
  name: string;
  quantity: number;
  part_number?: string | null;
  requirements: ProductRequirement[];
  node_names: string[];
  explode?: [number, number, number] | null;
  status: "proposed" | "confirmed";
}
export interface ProductDocument {
  document_id: string;
  name: string;
  kind: "blueprint" | "requirements" | "model";
  data_origin: "synthetic_demo" | "provided_document";
  media_type: string;
  size_bytes: number;
  content_url?: string | null;
  extraction_status: "pending" | "complete" | "unavailable";
  extraction_method?: string | null;
  excerpt?: string | null;
}
export interface ProductModel {
  origin: "prepared_demo" | "uploaded" | "generated";
  status: "missing" | "ready" | "provider_required";
  asset_url?: string | null;
  document_id?: string | null;
  source_url?: string | null;
  license?: string | null;
  notes?: string | null;
  node_names: string[];
  mapping_status: "mapped" | "unmapped" | "partial";
}
export interface ProductEvidence {
  requirement_key: string;
  status: "supported" | "unknown" | "conflict";
  note: string;
  source_url?: string | null;
}
export interface ProductCandidate {
  candidate_id: string;
  part_id: string;
  supplier_name: string;
  route: "buy" | "make";
  country?: string | null;
  price?: number | null;
  currency?: string | null;
  lead_time_days?: number | null;
  summary: string;
  source_url?: string | null;
  data_origin: "synthetic_demo" | "public_web";
  eligibility: "unverified";
  evidence: ProductEvidence[];
  retrieved_at?: string | null;
}
export interface ProductInvestigation {
  part_id: string;
  job_id: string;
  mode?: "demo" | "live";
  status: "queued" | "running" | "complete" | "failed";
  stage: string;
  summary?: string | null;
  candidates: ProductCandidate[];
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
  providers_used: string[];
}
export interface ProductPackageItem {
  part_id: string;
  part_name: string;
  quantity: number;
  supplier_name: string;
  candidate_id: string;
  data_origin: "synthetic_demo" | "public_web";
  requirements: ProductRequirement[];
  evidence_gaps: string[];
  rfq_text: string;
}
export interface ProductPackage {
  package_id: string;
  status: "draft" | "approved" | "simulated";
  input_version: number;
  items: ProductPackageItem[];
  created_at: string;
  approved_at?: string | null;
  approved_by?: string | null;
  approval_scope: "simulation_only";
  simulated_at?: string | null;
  receipt?: string | null;
  notice: string;
}
export interface ProductEvent {
  sequence: number;
  type: string;
  summary: string;
  part_id?: string | null;
  created_at: string;
}
export interface ProductCapabilities {
  document_parsing: string;
  requirement_extraction: string;
  supplier_discovery: string;
  model_generation: "provider_required";
  storage: "lakebase_postgres" | "local_sqlite";
  execution: "durable_queue" | "local_worker";
}
export interface ProductProject {
  project_id: string;
  name: string;
  demo_id?: string | null;
  product_type: string;
  version: number;
  input_version: number;
  status:
    | "draft"
    | "extracting"
    | "review"
    | "ready"
    | "investigating"
    | "results"
    | "packaged";
  documents: ProductDocument[];
  parts: ProductPart[];
  model: ProductModel;
  research: ProductInvestigation[];
  selections: Record<string, string>;
  package?: ProductPackage | null;
  events: ProductEvent[];
  capabilities: ProductCapabilities;
  created_at: string;
  updated_at: string;
}
export interface DemoProduct {
  demo_id: string;
  name: string;
  description: string;
  product_type: string;
  part_count: number;
  model: ProductModel;
  data_origin: "synthetic_demo";
}
