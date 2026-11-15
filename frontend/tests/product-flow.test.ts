import { test } from "node:test";
import assert from "node:assert/strict";
import { createProductApi } from "../src/product-flow/client.ts";
import { candidateFindings } from "../src/product-flow/geography.ts";
import type { ProductProject } from "../src/product-flow/types.ts";

test("product requests retain project scope, reviewed version, and explicit research mode", async () => {
  const calls: { url: string; init: RequestInit }[] = [];
  const api = createProductApi("/api/v1/products", async (url, init) => {
    calls.push({ url: String(url), init: init ?? {} });
    return new Response(JSON.stringify({ project_id: "project/1" }), {
      status: 200,
    });
  });
  await api.parts("project/1", [], true, 7);
  await api.investigate("project/1", ["lamp-shade", "lamp-frame"], "live");
  assert.equal(calls[0].url, "/api/v1/products/project%2F1/parts");
  assert.equal(calls[0].init.method, "PATCH");
  assert.deepEqual(JSON.parse(String(calls[0].init.body)), {
    parts: [],
    confirm: true,
    expected_version: 7,
  });
  assert.deepEqual(JSON.parse(String(calls[1].init.body)), {
    part_ids: ["lamp-shade", "lamp-frame"],
    mode: "live",
  });
  assert.equal(calls[0].init.credentials, "same-origin");
  assert.notEqual(
    new Headers(calls[0].init.headers).get("Idempotency-Key"),
    new Headers(calls[1].init.headers).get("Idempotency-Key"),
  );
});

test("failed mutations are reported without silently retrying or approving", async () => {
  let attempts = 0;
  const api = createProductApi("/api/v1/products", async () => {
    attempts++;
    return new Response(
      JSON.stringify({ message: "This package changed. Review it again." }),
      { status: 409 },
    );
  });
  await assert.rejects(api.approve("p", "package-1"), /This package changed/);
  assert.equal(attempts, 1);
});

test("country globe excludes unknown and unsourced live locations, and labels sample provenance", () => {
  const candidate = (overrides: object) => ({
    candidate_id: "c",
    part_id: "p",
    supplier_name: "Supplier",
    route: "buy",
    country: "Germany",
    data_origin: "public_web",
    source_url: "https://example.com/source",
    ...overrides,
  });
  const project = {
    project_id: "project",
    demo_id: "lamp",
    updated_at: "2026-11-15T00:00:00Z",
    research: [
      {
        part_id: "p",
        candidates: [
          candidate({ candidate_id: "sourced" }),
          candidate({ candidate_id: "no-source", source_url: null }),
          candidate({
            candidate_id: "unsafe",
            source_url: "javascript:alert(1)",
          }),
          candidate({ candidate_id: "unknown", country: "Unspecified" }),
          candidate({
            candidate_id: "sample",
            country: "United Kingdom",
            source_url: null,
            data_origin: "synthetic_demo",
          }),
        ],
      },
    ],
  } as ProductProject;
  const findings = candidateFindings(project);
  assert.deepEqual(
    findings.map((f) => f.event_id),
    ["sourced", "sample"],
  );
  assert.ok(
    findings.every(
      (f) =>
        Number.isFinite(f.location.latitude) &&
        Number.isFinite(f.location.longitude),
    ),
  );
  assert.ok(findings.every((f) => f.location.precision === "representative"));
  assert.equal(findings[1].location.data_origin, "synthetic_demo");
  assert.equal(findings[0].location.source, "https://example.com/source");
});

test("approval and simulation bind to the package the user reviewed", async () => {
  const payloads: unknown[] = [];
  const api = createProductApi("/api/v1/products", async (_url, init) => {
    payloads.push(JSON.parse(String(init?.body)));
    return new Response(JSON.stringify({}), { status: 200 });
  });
  await api.approve("p", "package-v2");
  await api.simulate("p", "package-v2");
  assert.deepEqual(payloads, [
    { acknowledge_unverified: true, expected_package_id: "package-v2" },
    { expected_package_id: "package-v2" },
  ]);
});

test("agent controls bind mandate version and run identity without purchase authorization", async () => {
  const calls: { url: string; body: unknown }[] = [];
  const api = createProductApi("/api/v1/products", async (url, init) => {
    calls.push({ url: String(url), body: JSON.parse(String(init?.body)) });
    return new Response("{}", { status: 200 });
  });
  await api.startAgent("project/one", 12, "live");
  await api.pauseAgent("project/one", "run-one", 14);
  await api.resumeAgent("project/one", "run-one", 15);
  assert.deepEqual(calls, [
    {
      url: "/api/v1/products/project%2Fone/agent/start",
      body: { expected_version: 12, mode: "live" },
    },
    {
      url: "/api/v1/products/project%2Fone/agent/pause",
      body: { expected_run_id: "run-one", expected_version: 14 },
    },
    {
      url: "/api/v1/products/project%2Fone/agent/resume",
      body: { expected_run_id: "run-one", expected_version: 15 },
    },
  ]);
});

test("agent command conflicts surface once without retrying stale mandates", async () => {
  let attempts = 0;
  const api = createProductApi("/api/v1/products", async () => {
    attempts++;
    return new Response(
      JSON.stringify({
        message: "The agent run changed. Refresh before resuming.",
      }),
      { status: 409 },
    );
  });
  await assert.rejects(api.resumeAgent("p", "old-run", 2), /run changed/);
  assert.equal(attempts, 1);
});
