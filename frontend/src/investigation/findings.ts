import type { DomainEvent, Schema } from "../api/types.ts";
export type Finding = Schema<"SupplierDiscovery"> & {
  event_id: string;
  evidence_refs: string[];
  occurred_at: string;
  case_id: string;
};
export function batchEvents(
  events: DomainEvent[],
  batch: Schema<"BatchInvestigation">,
): DomainEvent[] {
  const scoped = events.filter((e) => e.scenario_run_id === batch.run_id);
  const belongs = (e: DomainEvent) =>
    batch.components.some(
      (c) =>
        c.case_id === e.case_id &&
        !!c.generation_id &&
        (e.invocation_id === c.generation_id ||
          e.data?.generation_id === c.generation_id),
    );
  // A decision is emitted before run.completed. Keep raw history in the hook so
  // completion can prove that earlier decision belongs to this exact generation.
  const decisions = new Set(
    scoped
      .filter(
        (e) =>
          e.type === "run.completed" &&
          belongs(e) &&
          typeof e.data?.decision_id === "string",
      )
      .map((e) => `${e.case_id}:${e.data.decision_id}`),
  );
  return scoped.filter(
    (e) =>
      belongs(e) ||
      (["decision.created", "decision.updated"].includes(e.type) &&
        typeof e.data?.decision_id === "string" &&
        decisions.has(`${e.case_id}:${e.data.decision_id}`)),
  );
}
// Later case activity is a separate notice, never evidence belonging to this batch.
export function outsideBatchCases(
  events: DomainEvent[],
  batch: Schema<"BatchInvestigation">,
): string[] {
  return [
    ...new Set(
      events
        .filter(
          (e) =>
            e.scenario_run_id === batch.run_id &&
            e.occurred_at >= batch.created_at &&
            batch.components.some(
              (c) =>
                c.case_id === e.case_id &&
                ((!!(e.invocation_id || e.data?.generation_id) &&
                  (e.invocation_id || e.data?.generation_id) !==
                    c.generation_id) ||
                  [
                    "signal.received",
                    "selection.stale",
                    "impact.detected",
                  ].includes(e.type)),
            ),
        )
        .map((e) => e.case_id),
    ),
  ];
}
export function supplierFindings(events: DomainEvent[]): Finding[] {
  const found = new Map<string, Finding>();
  for (const e of events) {
    if (e.type !== "supplier.discovered") continue;
    const d = e.data as Partial<Schema<"SupplierDiscovery">>;
    if (
      typeof d.component_id !== "string" ||
      typeof d.candidate_id !== "string" ||
      typeof d.supplier_id !== "string" ||
      !d.location ||
      typeof d.location.site_id !== "string" ||
      !d.route
    )
      continue;
    found.set(`${d.component_id}:${d.candidate_id}:${d.location.site_id}`, {
      ...(d as Schema<"SupplierDiscovery">),
      event_id: e.event_id,
      evidence_refs: e.evidence_refs ?? [],
      occurred_at: e.occurred_at,
      case_id: e.case_id,
    });
  }
  return [...found.values()];
}
export function knownLocation(f: Finding): boolean {
  const l = f.location;
  return (
    !!l.source &&
    typeof l.latitude === "number" &&
    Number.isFinite(l.latitude) &&
    Math.abs(l.latitude) <= 90 &&
    typeof l.longitude === "number" &&
    Number.isFinite(l.longitude) &&
    Math.abs(l.longitude) <= 180
  );
}
