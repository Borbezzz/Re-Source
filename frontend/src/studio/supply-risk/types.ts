export interface RiskNeed { part_id: string; quantity: number; destination: string; need_by: string }
export interface RiskEvidence {
  evidence_id: string; part_id: string;
  kind: "quote" | "backorder" | "shipment" | "delivery" | "route_disruption" | "material_trend" | "freight_pressure";
  title: string; excerpt: string; issued_on: string | null; source_url?: string | null;
  source_document_id?: string | null; source_version: string;
  supplier?: string | null; part_number?: string | null; revision?: string | null;
  quantity?: number | null; destination?: string | null; route?: string | null;
  arrival_on?: string | null; event?: string | null; origin: "provided_document" | "synthetic_demo";
}
export interface RiskObservation { evidence: RiskEvidence; level: "alert" | "watchlist" | "matched" | "superseded"; applies_because: string; days_late: number | null }
export interface RiskPart {
  part_id: string; name: string; part_number: string | null; revision: string | null; need: RiskNeed;
  status: "at_risk" | "watchlist" | "unknown" | "on_time" | "received";
  summary: string; missing: string[]; exposure: string[]; observations: RiskObservation[]; actions: string[];
}
export interface RiskSource { title: string; url: string; excerpt: string; publisher: string; published_on: string | null; retrieved_at: string; provider: string }
export interface RiskScan {
  project_id: string; project_version: number; version: number; status: "not_started" | "current" | "needs_confirmation";
  evaluated_at: string; searched_at: string | null; parts: RiskPart[]; sources: RiskSource[];
  providers: { name: string; status: "searched" | "unavailable" | "not_configured"; source_count: number }[];
}
export interface NeedsDraft {
  destination: string; need_by: string;
  parts: { part_id: string; part_number: string; revision: string; quantity: number }[];
}
export const RISK_LABELS: Record<RiskPart["status"], string> = {
  at_risk: "Delivery at risk", watchlist: "Watchlist", unknown: "Arrival unknown", on_time: "Quoted on time", received: "Receipt recorded",
};
export const dateLabel = (value: string | null | undefined) => value ? new Date(value.slice(0, 10) + "T12:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" }) : "Date unknown";
