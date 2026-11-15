import type {
  CaseView,
  Decision,
  DecisionSummary,
  DocumentsView,
  DomainEvent,
  EngineView,
  Schema,
  VisualAction,
} from "./types.ts";

export class ApiFailure extends Error {
  readonly status: number;
  readonly detail: Schema<"ApiError">;
  constructor(status: number, detail: Schema<"ApiError">) {
    super(detail.message);
    this.name = "ApiFailure";
    this.status = status;
    this.detail = detail;
  }
}

export interface Command<T> {
  key: string;
  execute: (signal?: AbortSignal) => Promise<T>;
}

const part = encodeURIComponent;
const runQuery = (runId?: string) => (runId ? `?run_id=${part(runId)}` : "");

export function createApi(base = "/api/v1", transport: typeof fetch = fetch) {
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await transport(`${base}${path}`, init);
    const body: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      const error =
        body && typeof body === "object"
          ? (body as Partial<Schema<"ApiError">>)
          : {};
      throw new ApiFailure(response.status, {
        code: error.code ?? "HTTP_ERROR",
        message: error.message ?? `Request failed (${response.status})`,
        retryable: error.retryable ?? response.status >= 500,
        details: error.details ?? {},
        correlation_id: error.correlation_id ?? "",
        case_revision: error.case_revision,
      });
    }
    return body as T;
  }
  function command<T>(
    path: string,
    body: unknown,
    method = "POST",
  ): Command<T> {
    // Snapshot the payload and IDs once. Explicit retry reuses this exact command;
    // a new action must construct a new command. No automatic mutation retries.
    const key = crypto.randomUUID();
    const correlationId = crypto.randomUUID();
    const payload = JSON.stringify(body);
    return {
      key,
      execute: (signal) =>
        request<T>(path, {
          method,
          body: payload,
          signal,
          headers: {
            "Content-Type": "application/json",
            "Idempotency-Key": key,
            "X-Correlation-Id": correlationId,
          },
        }),
    };
  }
  const get = <T>(path: string, signal?: AbortSignal) =>
    request<T>(path, { signal });
  return {
    assemblies: (signal?: AbortSignal) =>
      get<Schema<"AssemblyProfile">[]>("/assemblies", signal),
    batch: (id: string, signal?: AbortSignal) =>
      get<Schema<"BatchInvestigation">>(`/batches/${part(id)}`, signal),
    startBatch: (body: Schema<"BatchInvestigationRequest">) =>
      command<Schema<"BatchInvestigation">>("/batches", body),
    upload: (
      file: File,
      kind: Schema<"IntakeUpload">["kind"],
      componentId?: string,
    ): Command<Schema<"IntakeUpload">> => {
      const form = new FormData();
      form.set("file", file);
      form.set("kind", kind);
      form.set("engine_id", "engine-demo-001");
      if (componentId) form.set("component_id", componentId);
      const key = crypto.randomUUID();
      return {
        key,
        execute: (signal) =>
          request("/intake/uploads", {
            method: "POST",
            body: form,
            signal,
            headers: { "Idempotency-Key": key },
          }),
      };
    },
    uploadStatus: (id: string, signal?: AbortSignal) =>
      get<Schema<"IntakeUpload">>(`/intake/uploads/${part(id)}`, signal),
    uploadUrl: (id: string) => `${base}/intake/uploads/${part(id)}/content`,
    extractRequirements: (uploadId: string, componentId: string) =>
      command<Schema<"PartRequirementDraft">>("/intake/part-requirements", {
        upload_id: uploadId,
        component_id: componentId,
      }),
    requirementDraft: (id: string, signal?: AbortSignal) =>
      get<Schema<"PartRequirementDraft">>(
        `/intake/part-requirements/${part(id)}`,
        signal,
      ),
    patchRequirements: (
      draft: Schema<"PartRequirementDraft">,
      fieldEdits: Record<string, unknown>,
      action?: "confirm" | "reject",
    ) =>
      command<Schema<"PartRequirementDraft">>(
        `/intake/part-requirements/${part(draft.draft_id)}`,
        {
          expected_version: draft.version,
          field_edits: fieldEdits,
          action,
          actor: "demo-operator",
        },
        "PATCH",
      ),
    meshJob: (uploadId: string, expected?: Schema<"MeshExpectation">[]) =>
      command<Schema<"MeshJob">>("/intake/mesh-jobs", {
        upload_id: uploadId,
        engine_id: "engine-demo-001",
        expected,
      }),
    meshJobStatus: (id: string, signal?: AbortSignal) =>
      get<Schema<"MeshJob">>(`/intake/mesh-jobs/${part(id)}`, signal),
    activateMesh: (id: string) =>
      command<Schema<"ManifestProvenance">>(
        `/intake/mesh-jobs/${part(id)}/activate`,
        {},
      ),
    manifest: (signal?: AbortSignal) =>
      get<Schema<"ManifestProvenance">>("/intake/manifest", signal),
    engine: (runId?: string, signal?: AbortSignal) =>
      get<EngineView>(`/engines/engine-demo-001${runQuery(runId)}`, signal),
    case: (id: string, runId?: string, signal?: AbortSignal) =>
      get<CaseView>(`/cases/${part(id)}${runQuery(runId)}`, signal),
    decisions: (id: string, runId?: string, signal?: AbortSignal) =>
      get<DecisionSummary[]>(
        `/cases/${part(id)}/decisions${runQuery(runId)}`,
        signal,
      ),
    decision: (
      id: string,
      decisionId: string,
      runId?: string,
      signal?: AbortSignal,
    ) =>
      get<Decision>(
        `/cases/${part(id)}/decisions/${part(decisionId)}${runQuery(runId)}`,
        signal,
      ),
    documents: (id: string, runId?: string, signal?: AbortSignal) =>
      get<DocumentsView>(
        `/cases/${part(id)}/documents${runQuery(runId)}`,
        signal,
      ),
    evidence: (id: string, signal?: AbortSignal) =>
      get<Schema<"EvidenceView">>(`/evidence/${part(id)}`, signal),
    history: (id: string, runId: string, signal?: AbortSignal) =>
      get<DomainEvent[]>(
        `/cases/${part(id)}/events/history?run_id=${part(runId)}&limit=5000`,
        signal,
      ),
    diff: (
      id: string,
      from: string,
      to: string,
      runId: string,
      signal?: AbortSignal,
    ) =>
      get<Schema<"DecisionDiff">>(
        `/cases/${part(id)}/diff?from=${part(from)}&to=${part(to)}&run_id=${part(runId)}`,
        signal,
      ),
    readiness: (signal?: AbortSignal) =>
      get<Schema<"Readiness">>("/readiness", signal),
    currentRun: (signal?: AbortSignal) =>
      get<Schema<"ScenarioRunView">>("/scenario-runs/current", signal),
    newRun: (mode: Schema<"Mode"> = "seeded", replaySource?: string) =>
      command<Schema<"ScenarioRunView">>("/scenario-runs", {
        mode,
        manifest_id: "engine-demo-001",
        fixture_version: "seed-v1",
        replay_source_run_id: replaySource,
      }),
    investigate: (view: CaseView) =>
      command<Schema<"CommandAccepted">>(
        `/cases/${part(view.case_id)}/investigations`,
        { expected_revision: view.revision, mode: view.mode },
      ),
    select: (view: CaseView, decision: Decision, candidateId: string) =>
      command<Schema<"Selection">>(`/cases/${part(view.case_id)}/selections`, {
        candidate_id: candidateId,
        decision_id: decision.decision_id,
        evidence_hash: decision.evidence_hash,
        expected_revision: view.revision,
        actor: "demo-operator",
      }),
    visual: (id: string, action: VisualAction) =>
      command<Schema<"VisualActionResult">>(
        `/cases/${part(id)}/visual-actions`,
        { action },
      ),
    monitoring: (view: CaseView, status: Schema<"MonitoringStatus">) =>
      command<CaseView>(
        `/cases/${part(view.case_id)}/monitoring`,
        { expected_revision: view.revision, status },
        "PATCH",
      ),
    editDocument: (
      id: string,
      version: number,
      edits: Record<string, unknown>,
      action?: Schema<"DocumentPatchRequest">["review_action"],
    ) =>
      command<DocumentsView>(
        `/documents/${part(id)}`,
        {
          expected_version: version,
          field_edits: edits,
          review_action: action,
          actor: "demo-operator",
        },
        "PATCH",
      ),
    submit: (view: CaseView, pkg: Schema<"DocumentPackage">) =>
      command<Schema<"SimulatedReceipt">>(
        `/cases/${part(view.case_id)}/simulated-submissions`,
        {
          selection_id: view.current_selection?.selection_id,
          package_id: pkg.package_id,
          package_version: pkg.version,
        },
      ),
    injectSignal: (runId: string, fixtureSignalId: string) =>
      command<Schema<"SignalInjectionResult">>(
        `/scenario-runs/${part(runId)}/signals`,
        { fixture_signal_id: fixtureSignalId },
      ),
    evidenceChange: (runId: string, fixtureId: string) =>
      command<Schema<"SignalInjectionResult">>(
        `/scenario-runs/${part(runId)}/evidence-changes`,
        { fixture_evidence_change_id: fixtureId },
      ),
    advanceClock: (runId: string, hours: number) =>
      command<Schema<"ClockState">>(`/scenario-runs/${part(runId)}/clock`, {
        hours,
      }),
    packageUrl: (id: string) => `${base}/packages/${part(id)}/download`,
  };
}

export type RecoveryApi = ReturnType<typeof createApi>;
export const api = createApi();
