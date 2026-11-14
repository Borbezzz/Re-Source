import { useEffect, useRef, useState, useCallback } from "react";
import { api, ApiFailure, type Command } from "./client.ts";
import { mergeEvents, watchEvents, type ConnectionState } from "./events.ts";
import type {
  CaseView,
  Decision,
  DecisionSummary,
  DocumentsView,
  DomainEvent,
} from "./types.ts";

export function useCase(caseId: string, runId: string) {
  const [view, setView] = useState<CaseView | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [history, setHistory] = useState<DecisionSummary[]>([]);
  const [documents, setDocuments] = useState<DocumentsView | null>(null);
  const [events, setEvents] = useState<DomainEvent[]>([]);
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [loadError, setLoadError] = useState<string | null>(null);
  const refreshRef = useRef<() => Promise<void>>(async () => {});
  useEffect(() => {
    const abort = new AbortController();
    let active = true,
      loading = false,
      dirty = false,
      close: undefined | (() => void);
    setView(null);
    setDecision(null);
    setDocuments(null);
    setHistory([]);
    setEvents([]);
    setLoadError(null);
    const refresh = async () => {
      if (!active) return;
      if (loading) {
        dirty = true;
        return;
      }
      loading = true;
      try {
        do {
          dirty = false;
          const v = await api.case(caseId, runId, abort.signal);
          const [d, docs, h] = await Promise.all([
            v.current_decision_id
              ? api.decision(caseId, v.current_decision_id, runId, abort.signal)
              : null,
            api.documents(caseId, runId, abort.signal),
            api.decisions(caseId, runId, abort.signal),
          ]);
          if (active && v.scenario_run_id === runId && v.case_id === caseId) {
            setView(v);
            setDecision(d);
            setDocuments(docs);
            setHistory(h);
            setLoadError(null);
          }
        } while (dirty && active);
      } catch (e) {
        if (active)
          setLoadError(
            e instanceof Error ? e.message : "Unable to refresh this case.",
          );
      } finally {
        loading = false;
      }
    };
    refreshRef.current = refresh;
    void (async () => {
      await refresh();
      let cursor = 0;
      try {
        const h = await api.history(caseId, runId, abort.signal);
        if (!active) return;
        const clean = mergeEvents([], h, caseId, runId);
        setEvents(clean);
        cursor = clean.at(-1)?.sequence ?? 0;
      } catch (e) {
        if (active)
          setLoadError(
            "Activity history could not be loaded. Reconnecting from the beginning.",
          );
      }
      if (!active) return;
      close = watchEvents({
        caseId,
        runId,
        after: cursor,
        onConnection: setConnection,
        onSnapshotRequired: () => {
          void refresh();
        },
        onEvent: (e) => {
          setEvents((prev) => mergeEvents(prev, [e], caseId, runId));
          // Coalesce concurrent snapshots; completed events trigger authoritative
          // projections. No progress percentage or visual result is inferred here.
          if (!e.type.endsWith(".started")) void refresh();
        },
      });
    })();
    return () => {
      active = false;
      abort.abort();
      close?.();
    };
  }, [caseId, runId]);
  const refresh = useCallback(() => refreshRef.current(), []);
  return {
    view,
    decision,
    history,
    documents,
    events,
    connection,
    loadError,
    refresh,
  };
}

export function useCommand(refresh: () => Promise<void>) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState<string | null>(null);
  const last = useRef<Command<unknown> | null>(null),
    active = useRef(true),
    locked = useRef(false);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  const execute = async (command: Command<unknown>) => {
    if (locked.current) return false;
    locked.current = true;
    last.current = command;
    setBusy(true);
    setError(null);
    try {
      await command.execute();
      if (active.current) {
        last.current = null;
        await refresh();
      }
      return true;
    } catch (e) {
      if (active.current) {
        setError(
          e instanceof Error
            ? e.message
            : "The request could not be completed.",
        );
        if (e instanceof ApiFailure && !e.detail.retryable) last.current = null;
        await refresh();
      }
      return false;
    } finally {
      locked.current = false;
      if (active.current) setBusy(false);
    }
  };
  return {
    busy,
    error,
    execute,
    canRetry: !!last.current,
    retry: () =>
      last.current ? execute(last.current) : Promise.resolve(false),
    clearError: () => setError(null),
  };
}
