import { test } from "node:test";
import assert from "node:assert/strict";
import { createApi, ApiFailure } from "../src/api/client.ts";
import {
  formatMoney,
  selectionBlock,
  submissionBlock,
  sourceUrl,
  meshSourceBlock,
} from "../src/api/guards.ts";

test("explicit retry preserves idempotency key, correlation and body; new actions have new keys", async () => {
  const requests: RequestInit[] = [];
  const client = createApi("/api", async (_url, init) => {
    requests.push(init!);
    return new Response("{}");
  });
  const command = client.newRun();
  await command.execute();
  await command.execute();
  await client.newRun().execute();
  assert.deepEqual(requests[0].headers, requests[1].headers);
  assert.equal(requests[0].body, requests[1].body);
  assert.notDeepEqual(requests[0].headers, requests[2].headers);
});
test("stale decisions and incomplete evidence cannot be selected", () => {
  const view: any = {
    case_id: "c",
    scenario_run_id: "r",
    pending_change_ids: [],
    current_decision_id: "d",
    input_revision: 1,
    stale_reasons: [],
  };
  const decision: any = {
    case_id: "c",
    scenario_run_id: "r",
    decision_id: "d",
    input_revision: 1,
    status: "current",
  };
  assert.equal(
    selectionBlock(view, decision, {
      eligibility: "eligible",
      feasible: true,
    } as any),
    null,
  );
  assert.match(
    selectionBlock(view, { ...decision, input_revision: 0 }, {
      eligibility: "eligible",
    } as any)!,
    /superseded/,
  );
  assert.match(
    selectionBlock(view, decision, { eligibility: "pending" } as any)!,
    /missing/,
  );
  assert.match(
    selectionBlock({ ...view, pending_change_ids: ["new"] }, decision, {
      eligibility: "eligible",
    } as any)!,
    /reconciled/,
  );
});
test("package approval is bound to exact hash and selection", () => {
  const v: any = {
    scenario_run_id: "r",
    pending_change_ids: [],
    current_package_id: "p",
    current_selection: { selection_id: "s", status: "current" },
  };
  const p: any = {
    package_id: "p",
    scenario_run_id: "r",
    selection_id: "s",
    status: "current",
    review_state: "approved",
    package_hash: "h",
    approved_hash: "h",
  };
  assert.equal(submissionBlock(v, p), null);
  assert.match(submissionBlock(v, { ...p, package_hash: "new" })!, /exact/);
});
test("money keeps decimal precision and evidence URLs reject script schemes", () => {
  assert.equal(
    formatMoney({ amount: "9007199254740993.15", currency: "GBP" }),
    "£9,007,199,254,740,993.15",
  );
  assert.equal(sourceUrl("javascript:alert(1)"), undefined);
  assert.equal(
    sourceUrl("https://example.com/evidence"),
    "https://example.com/evidence",
  );
});
test("API failures retain server stale-state detail", async () => {
  const client = createApi(
    "/api",
    async () =>
      new Response(
        JSON.stringify({
          code: "STALE",
          message: "Refresh the decision",
          retryable: false,
          details: {},
        }),
        { status: 409 },
      ),
  );
  await assert.rejects(
    client.newRun().execute(),
    (e) =>
      e instanceof ApiFailure && e.status === 409 && e.detail.code === "STALE",
  );
});

test("mesh activation requires current blueprint identity citations, not just structural success", () => {
  const job: any = {
    status: "succeeded",
    expected: [{ component_id: "c", node_name: "part" }],
    validation: {
      ok: true,
      checks: [
        {
          component_id: "c",
          node_name: "part",
          ok: true,
          source_ref: { upload_id: "blueprint", page: 1, excerpt: "Part 7" },
        },
      ],
    },
  };
  assert.equal(meshSourceBlock(job, "blueprint"), null);
  assert.match(meshSourceBlock(job, "different")!, /uploaded blueprint/);
  job.validation.checks[0].source_ref = { upload_id: "blueprint" };
  assert.match(meshSourceBlock(job, "blueprint")!, /source page/);
  job.validation.checks = [];
  assert.match(meshSourceBlock(job, "blueprint")!, /unique validated/);
});
