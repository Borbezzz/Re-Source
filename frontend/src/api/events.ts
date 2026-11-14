import type { DomainEvent } from "./types.ts";

export type ConnectionState =
  "connecting" | "connected" | "reconnecting" | "closed";

// Every reducer is scoped to one case and run. Never carry another case's cursor
// into a new connection; event IDs alone are insufficient for snapshot isolation.
export function mergeEvents(
  previous: DomainEvent[],
  incoming: DomainEvent[],
  caseId: string,
  runId: string,
): DomainEvent[] {
  const seen = new Map<string, DomainEvent>();
  for (const event of [...previous, ...incoming]) {
    if (event.case_id === caseId && event.scenario_run_id === runId)
      seen.set(event.event_id, event);
  }
  return [...seen.values()].sort((a, b) => a.sequence - b.sequence);
}

export function decodeEvent(
  data: string,
  caseId: string,
  runId: string,
): DomainEvent | null {
  try {
    const e = JSON.parse(data);
    if (
      !e ||
      typeof e.event_id !== "string" ||
      !Number.isSafeInteger(e.sequence) ||
      e.case_id !== caseId ||
      e.scenario_run_id !== runId ||
      typeof e.type !== "string" ||
      typeof e.summary !== "string"
    )
      return null;
    return e as DomainEvent;
  } catch {
    return null;
  }
}

export const domainEventNames = [
  "case.started",
  "task.started",
  "task.completed",
  "task.failed",
  "tool.started",
  "tool.completed",
  "tool.failed",
  "evidence.ingested",
  "evidence.extracted",
  "evidence.validated",
  "supplier.discovered",
  "gap.opened",
  "gap.resolved",
  "check.completed",
  "signal.received",
  "signal.matched",
  "impact.detected",
  "reassessment.started",
  "decision.created",
  "decision.updated",
  "selection.accepted",
  "selection.stale",
  "documents.preparing",
  "documents.ready",
  "documents.stale",
  "submission.simulated",
  "visual.updated",
  "monitoring.updated",
  "case.state_changed",
  "run.interrupted",
  "run.recovered",
  "run.completed",
  "run.failed",
  "intake.uploaded",
  "intake.extracted",
  "intake.validated",
  "intake.confirmed",
  "manifest.updated",
];

export function watchEvents(options: {
  caseId: string;
  runId: string;
  after?: number;
  onEvent: (event: DomainEvent) => void;
  onSnapshotRequired: () => void;
  onConnection: (state: ConnectionState) => void;
  createSource?: (url: string) => EventSource;
  streamPath?: string;
}) {
  const { caseId, runId, onEvent, onSnapshotRequired, onConnection } = options;
  const params = new URLSearchParams({ run_id: runId });
  if (options.after != null) params.set("after", String(options.after));
  const source = (options.createSource ?? ((url) => new EventSource(url)))(
    `${options.streamPath ?? `/api/v1/cases/${encodeURIComponent(caseId)}/events`}?${params}`,
  );
  let active = true;
  onConnection("connecting");
  const receive = (message: MessageEvent) => {
    if (!active) return;
    const event = decodeEvent(message.data, caseId, runId);
    if (event) onEvent(event);
  };
  source.onmessage = receive;
  for (const type of domainEventNames)
    source.addEventListener(type, receive as EventListener);
  const snapshot = () => {
    if (active) onSnapshotRequired();
  };
  source.addEventListener("control", snapshot);
  source.addEventListener("control.snapshot_required", snapshot);
  source.onopen = () => {
    if (active) onConnection("connected");
  };
  source.onerror = () => {
    if (active)
      onConnection(source.readyState === 2 ? "closed" : "reconnecting");
  };
  // EventSource owns network reconnect/Last-Event-ID. No duplicate polling timer.
  return () => {
    active = false;
    source.close();
  };
}
