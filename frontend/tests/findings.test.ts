import { test } from "node:test";
import assert from "node:assert/strict";
import {
  batchEvents,
  outsideBatchCases,
  knownLocation,
  supplierFindings,
} from "../src/investigation/findings.ts";
const event = (overrides: any = {}) =>
  ({
    event_id: "e",
    scenario_run_id: "run",
    case_id: "case",
    invocation_id: "gen",
    sequence: 1,
    occurred_at: "2026-11-14T10:00:00Z",
    type: "supplier.discovered",
    data: {
      component_id: "part",
      candidate_id: "offer",
      supplier_id: "supplier",
      route: "BUY",
      location: {
        site_id: "site",
        latitude: 52,
        longitude: 0,
        source: "fixture:sites",
        precision: "representative",
        data_origin: "synthetic_demo",
      },
    },
    evidence_refs: ["doc"],
    ...overrides,
  }) as any;
test("batch findings reject other runs and cases and other generations while separately flagging later case activity", () => {
  const batch: any = {
    run_id: "run",
    created_at: "2026-11-14T10:01:00Z",
    components: [{ case_id: "case", generation_id: "gen" }],
  };
  const events = [
    event(),
    event({ event_id: "other-run", scenario_run_id: "other" }),
    event({ event_id: "other-case", case_id: "other" }),
    event({ event_id: "old", invocation_id: "old" }),
    event({
      event_id: "reassessed",
      invocation_id: "new",
      occurred_at: "2026-11-14T10:03:00Z",
    }),
  ];
  assert.deepEqual(
    batchEvents(events, batch).map((e) => e.event_id),
    ["e"],
  );
  assert.deepEqual(outsideBatchCases(events, batch), ["case"]);
});
test("geographic display requires sourced finite coordinates and retains unknown findings in the list", () => {
  const found = supplierFindings([
    event(),
    event({ event_id: "new", sequence: 2 }),
  ]);
  assert.equal(found.length, 1);
  assert.equal(found[0].event_id, "new");
  assert.equal(knownLocation(found[0]), true);
  for (const patch of [
    { latitude: null },
    { latitude: NaN },
    { longitude: 181 },
    { source: null },
  ])
    assert.equal(
      knownLocation({
        ...found[0],
        location: { ...found[0].location, ...patch },
      } as any),
      false,
    );
  assert.equal(supplierFindings([event({ data: {} })]).length, 0);
});

test("generation completion proves decision attribution regardless of event arrival order", () => {
  const batch: any = {
    run_id: "run",
    components: [{ case_id: "case", generation_id: "gen" }],
  };
  const decision = event({
    event_id: "decision",
    type: "decision.created",
    invocation_id: null,
    data: { decision_id: "D1" },
  });
  const completion = event({
    event_id: "completion",
    type: "run.completed",
    invocation_id: null,
    data: { generation_id: "gen", decision_id: "D1" },
  });
  const unrelated = event({
    event_id: "unrelated",
    type: "decision.updated",
    invocation_id: null,
    data: { decision_id: "D2" },
  });
  const otherCompletion = event({
    event_id: "other-completion",
    type: "run.completed",
    invocation_id: null,
    data: { generation_id: "other", decision_id: "D2" },
  });
  assert.deepEqual(batchEvents([decision], batch), []);
  assert.deepEqual(
    batchEvents([decision, unrelated, otherCompletion, completion], batch).map(
      (e) => e.event_id,
    ),
    ["decision", "completion"],
  );
});
