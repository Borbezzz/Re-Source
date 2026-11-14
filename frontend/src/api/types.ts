import type { components } from "../../../contracts/generated-types/api.ts";

export type Schema<K extends keyof components["schemas"]> =
  components["schemas"][K];
export type CaseView = Schema<"CaseView">;
export type EngineView = Schema<"EngineView">;
export type Decision = Schema<"DecisionSnapshot">;
export type RankedCandidate = Schema<"RankedCandidate">;
export type DocumentsView = Schema<"DocumentsView">;
export type ComponentInstance = Schema<"ComponentInstance">;
export type VisualAction = Schema<"VisualActionRequest">["action"];
export type DecisionSummary = Pick<
  Decision,
  | "decision_id"
  | "label"
  | "status"
  | "created_at"
  | "preferred_candidate_id"
  | "trigger_id"
  | "summary"
  | "input_revision"
  | "case_revision"
  | "evidence_hash"
>;

// DomainEvent is defined by models.py but is absent from FastAPI's generated
// OpenAPI components because SSE and history currently have untyped responses.
export interface DomainEvent {
  schema_version: string;
  event_id: string;
  sequence: number;
  occurred_at: string;
  scenario_run_id: string;
  case_id: string;
  case_revision: number;
  invocation_id?: string | null;
  task_id?: string | null;
  type: string;
  summary: string;
  data: Record<string, unknown>;
  evidence_refs: string[];
  trace_id?: string | null;
  data_origin: Schema<"DataOrigin">;
}
