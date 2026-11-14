import { test, expect } from "@playwright/test";

// Explicit opt-in: this suite requires RS_PUBLIC_DEMO=1. It sends ordinary
// anonymous requests, with no stored login state or deployment bypass headers.
test.skip(
  process.env.RESOURCE_VERIFY_PUBLIC !== "1",
  "Enable public runtime verification explicitly",
);

test("anonymous visitors retain their own run and cannot read another visitor's upload", async ({
  page,
  browser,
  baseURL,
}) => {
  expect((await page.context().cookies()).length).toBe(0);
  const engineResponse = page.waitForResponse((r) =>
    r.url().includes("/engines/engine-demo-001"),
  );
  await page.goto("/");
  const response = await engineResponse;
  expect(response.status()).toBe(200);
  const firstRun = (await response.json()).scenario_run_id;
  const cookie = (await page.context().cookies()).find(
    (c) => c.name === "resource_visitor",
  );
  expect(Boolean(cookie)).toBe(true);
  expect(cookie?.httpOnly).toBe(true);
  expect(cookie?.sameSite).toBe("Lax");
  if (baseURL?.startsWith("https:")) expect(cookie?.secure).toBe(true);

  const uploaded = await page.request.post("/api/v1/intake/uploads", {
    multipart: {
      kind: "blueprint",
      file: {
        name: "public-isolation-test.txt",
        mimeType: "text/plain",
        buffer: Buffer.from(
          "Synthetic public isolation test; not engineering evidence.",
        ),
      },
    },
  });
  expect(uploaded.status()).toBe(201);
  const uploadId = (await uploaded.json()).upload_id;
  await page.reload();
  const ownEngine = await page.request.get("/api/v1/engines/engine-demo-001");
  expect((await ownEngine.json()).scenario_run_id).toBe(firstRun);
  const ownContent = await page.request.get(
    `/api/v1/intake/uploads/${uploadId}/content`,
  );
  expect(ownContent.status()).toBe(200);
  expect(await ownContent.text()).toContain("Synthetic public isolation test");

  const other = await browser.newContext({ baseURL });
  try {
    expect((await other.cookies()).length).toBe(0);
    const second = await other.request.get("/api/v1/engines/engine-demo-001");
    expect(second.status()).toBe(200);
    expect((await second.json()).scenario_run_id).not.toBe(firstRun);
    expect(
      (await other.request.get(`/api/v1/scenario-runs/${firstRun}`)).status(),
    ).toBe(404);
    expect(
      (
        await other.request.get(`/api/v1/intake/uploads/${uploadId}/content`)
      ).status(),
    ).toBe(404);
    expect(
      (
        await other.request.post("/api/v1/scenario-runs", {
          data: { mode: "replay", replay_source_run_id: firstRun },
        })
      ).status(),
    ).toBe(404);
  } finally {
    await other.close();
  }
});

test("native EventSource reconnects after the bounded response and receives new persisted events", async ({
  page,
}) => {
  const engineResponse = page.waitForResponse((r) =>
    r.url().includes("/engines/engine-demo-001"),
  );
  await page.goto("/");
  const response = await engineResponse;
  expect(response.status()).toBe(200);
  const runId = (await response.json()).scenario_run_id;
  const resumeHeaders: Promise<string | null>[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/cases/case-primary/events?")) {
      resumeHeaders.push(request.headerValue("last-event-id"));
    }
  });
  const received = await page.evaluate(async (runId: string) => {
    const viewResponse = await fetch(
      `/api/v1/cases/case-primary?run_id=${encodeURIComponent(runId)}`,
    );
    if (!viewResponse.ok)
      throw new Error(`Case snapshot HTTP ${viewResponse.status}`);
    const view = await viewResponse.json();
    // A new run has no case events yet. Commit one before opening the stream
    // so its first response gives EventSource an actual cursor to resume.
    const initial = await fetch("/api/v1/cases/case-primary/monitoring", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": crypto.randomUUID(),
      },
      body: JSON.stringify({
        status: "active",
        expected_revision: view.revision,
      }),
    });
    if (!initial.ok)
      throw new Error(`Initial monitoring command HTTP ${initial.status}`);
    const revision = (await initial.json()).case_revision;
    return new Promise<{ opens: number; first: number; last: number }>(
      (resolve, reject) => {
        const source = new EventSource(
          `/api/v1/cases/case-primary/events?run_id=${encodeURIComponent(runId)}`,
        );
        let opens = 0,
          first = 0;
        const finish = (error?: Error, last = 0) => {
          clearTimeout(deadline);
          source.close();
          if (error) reject(error);
          else resolve({ opens, first, last });
        };
        const deadline = setTimeout(
          () =>
            finish(
              new Error("SSE did not reconnect and deliver within 120 seconds"),
            ),
          120_000,
        );
        source.onmessage = (e) => {
          const event = JSON.parse(e.data);
          if (!first) first = event.sequence;
          if (opens >= 2 && event.type === "monitoring.updated")
            finish(undefined, event.sequence);
        };
        source.onopen = async () => {
          opens++;
          if (opens === 2) {
            try {
              const result = await fetch(
                "/api/v1/cases/case-primary/monitoring",
                {
                  method: "PATCH",
                  headers: {
                    "Content-Type": "application/json",
                    "Idempotency-Key": crypto.randomUUID(),
                  },
                  body: JSON.stringify({
                    status: "paused",
                    expected_revision: revision,
                  }),
                },
              );
              if (!result.ok)
                finish(new Error(`Monitoring command HTTP ${result.status}`));
            } catch (error) {
              finish(
                error instanceof Error
                  ? error
                  : new Error("Monitoring command failed"),
              );
            }
          }
        };
      },
    );
  }, runId);
  expect(received.opens).toBeGreaterThanOrEqual(2);
  expect(received.first).toBeGreaterThan(0);
  expect(received.last).toBeGreaterThan(received.first);
  expect(
    (await Promise.all(resumeHeaders)).some(
      (cursor) => Number(cursor) >= received.first,
    ),
  ).toBe(true);
});
