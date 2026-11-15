import { test } from "node:test";
import assert from "node:assert/strict";
import { decodeEvent, mergeEvents, watchEvents } from "../src/api/events.ts";
import type { DomainEvent } from "../src/api/types.ts";
const event = (
  id: string,
  sequence: number,
  caseId = "case-a",
  run = "run-a",
) =>
  ({
    event_id: id,
    sequence,
    case_id: caseId,
    scenario_run_id: run,
    type: "tool.completed",
    summary: "Verified",
  }) as DomainEvent;

test("replay is deduplicated, ordered and isolated across cases and resets", () => {
  const result = mergeEvents(
    [event("2", 2), event("old", 99, "case-a", "old-run")],
    [event("1", 1), event("2", 2), event("other", 10, "case-b")],
    "case-a",
    "run-a",
  );
  assert.deepEqual(
    result.map((e) => e.event_id),
    ["1", "2"],
  );
  assert.equal(decodeEvent("not json", "case-a", "run-a"), null);
  assert.equal(
    decodeEvent(JSON.stringify(event("wrong", 1, "case-b")), "case-a", "run-a"),
    null,
  );
});

test("stream uses cursor, handles both named and unnamed events, and ignores queued events after close", () => {
  const handlers = new Map<string, (e: { data: string }) => void>();
  let url = "",
    closed = false,
    snapshots = 0;
  const seen: string[] = [];
  const fake = {
    onmessage: null as any,
    onopen: null,
    onerror: null,
    readyState: 1,
    addEventListener: (name: string, fn: any) => handlers.set(name, fn),
    close: () => {
      closed = true;
    },
  };
  const stop = watchEvents({
    caseId: "case-a",
    runId: "run-a",
    after: 8,
    onEvent: (e) => seen.push(e.event_id),
    onConnection: () => {},
    onSnapshotRequired: () => snapshots++,
    createSource: (u) => {
      url = u;
      return fake as any;
    },
  });
  assert.match(url, /after=8/);
  fake.onmessage({ data: JSON.stringify(event("9", 9)) });
  handlers.get("tool.completed")!({ data: JSON.stringify(event("10", 10)) });
  handlers.get("control")!({ data: "{}" });
  stop();
  fake.onmessage({ data: JSON.stringify(event("11", 11)) });
  assert.deepEqual(seen, ["9", "10"]);
  assert.equal(snapshots, 1);
  assert.equal(closed, true);
});
