import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client.ts";
import {
  mergeEvents,
  watchEvents,
  type ConnectionState,
} from "../api/events.ts";
import type { DomainEvent, Schema } from "../api/types.ts";
import { batchEvents, outsideBatchCases } from "./findings.ts";
export function useBatch(id: string) {
  const [attempt, setAttempt] = useState(0);
  const [batch, setBatch] = useState<Schema<"BatchInvestigation"> | null>(null);
  const [events, setEvents] = useState<DomainEvent[]>([]);
  const [connections, setConnections] = useState<
    Record<string, ConnectionState>
  >({});
  const [error, setError] = useState("");
  const [changedCases, setChangedCases] = useState<string[]>([]);
  useEffect(() => {
    const abort = new AbortController();
    let active = true,
      loading = false,
      dirty = false;
    const close: (() => void)[] = [];
    setBatch(null);
    setEvents([]);
    setChangedCases([]);
    setConnections({});
    setError("");
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
          const b = await api.batch(id, abort.signal);
          if (active) {
            setBatch(b);
            setError("");
          }
        } while (dirty && active);
      } catch (e) {
        if (active)
          setError(
            e instanceof Error ? e.message : "Unable to refresh research.",
          );
      } finally {
        loading = false;
      }
    };
    void (async () => {
      try {
        const b = await api.batch(id, abort.signal);
        if (!active) return;
        setBatch(b);
        await Promise.all(
          b.components.map(async (c) => {
            let history: DomainEvent[] = [];
            try {
              history = mergeEvents(
                [],
                await api.history(c.case_id, b.run_id, abort.signal),
                c.case_id,
                b.run_id,
              );
            } catch {
              if (active)
                setError(
                  "Some activity history could not load. The stream will replay it.",
                );
            }
            if (!active) return;
            const append = (incoming: DomainEvent[]) => {
              const changed = outsideBatchCases(incoming, b);
              if (changed.length)
                setChangedCases((prev) => [...new Set([...prev, ...changed])]);
              setEvents((prev) => {
                const scoped = mergeEvents(
                  prev.filter((e) => e.case_id === c.case_id),
                  incoming,
                  c.case_id,
                  b.run_id,
                );
                return [
                  ...prev.filter((e) => e.case_id !== c.case_id),
                  ...scoped,
                ].sort(
                  (a, z) =>
                    a.occurred_at.localeCompare(z.occurred_at) ||
                    a.sequence - z.sequence,
                );
              });
            };
            append(history);
            close.push(
              watchEvents({
                caseId: c.case_id,
                runId: b.run_id,
                after: history.at(-1)?.sequence ?? 0,
                onConnection: (s) =>
                  setConnections((prev) => ({ ...prev, [c.case_id]: s })),
                onSnapshotRequired: () => void refresh(),
                onEvent: (e) => {
                  append([e]);
                  if (
                    [
                      "task.started",
                      "task.completed",
                      "task.failed",
                      "tool.started",
                      "tool.completed",
                      "tool.failed",
                      "run.completed",
                      "run.failed",
                    ].includes(e.type)
                  )
                    void refresh();
                },
              }),
            );
          }),
        );
        await refresh();
      } catch (e) {
        if (active)
          setError(
            e instanceof Error
              ? e.message
              : "Unable to load this investigation.",
          );
      }
    })();
    return () => {
      active = false;
      abort.abort();
      close.forEach((f) => f());
    };
  }, [id, attempt]);
  return {
    batch,
    events: batch ? batchEvents(events, batch) : [],
    changedCases,
    connections,
    error,
    refresh: useCallback(async () => {
      setAttempt((n) => n + 1);
    }, []),
  };
}
