import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { addDays, assess, isoDay, pickAvailableSite, rankAll, type SourcingNeed } from "../src/studio/data/checks.ts";
import { DISRUPTION } from "../src/studio/data/sites.ts";
import type { ProductCandidate } from "../src/product-flow/types.ts";

const demo = JSON.parse(readFileSync(new URL("../../data/demo-products/turbofan.json", import.meta.url)).toString());
const offers = (demo.sample_offers ?? demo.parts.flatMap((p: { sample_offers?: unknown[] }) => p.sample_offers ?? [])) as ProductCandidate[];
const fanBlade = offers.filter((c) => c.candidate_id.startsWith("rs-tf-fan-blade-site-"));
const required = { partNumber: "RS-DEMO-FB-001", revision: "B", condition: "New" };
const today = new Date("2026-11-15T09:00:00Z");
const need = (quantity: number, days = 14): SourcingNeed => ({
  reason: "faulty",
  quantity,
  requiredBy: isoDay(addDays(today, days)),
  destination: "Filton, Bristol",
  budget: null,
});

const shortlist = (n: SourcingNeed, availableSite: string | null) =>
  rankAll(
    fanBlade.map((c) => assess(c, required, n, { today, availableSite })!).filter(Boolean),
    n,
    availableSite,
  );

test("fixture offers are present for the fan blade", () => {
  assert.ok(fanBlade.length >= 10, `expected fan blade sample offers, found ${fanBlade.length}`);
});

test("the chosen site is recommended even when no site would otherwise qualify", () => {
  const n = need(9); // no fan blade fixture holds 9 units
  assert.equal(shortlist(n, null).filter((a) => a.rank != null).length, 0);
  for (let i = 0; i < 25; i++) {
    const pick = pickAvailableSite(fanBlade, n, today);
    assert.ok(pick);
    const chosen = shortlist(n, pick).find((a) => a.candidate.candidate_id === pick)!;
    assert.equal(chosen.state, "eligible", chosen.reason);
    assert.ok(chosen.rank != null && chosen.rank <= 3);
    assert.ok(chosen.checks.every((c) => c.status === "pass" || c.status === "info"));
    assert.ok((chosen.site.stock ?? 0) >= 9);
    assert.equal(chosen.available, true);
    assert.match(chosen.checks.find((c) => c.id === "availability")!.note, /available now/);
  }
});

test("the pick varies between runs and never targets the disrupted site", () => {
  const n = need(1);
  const picks = new Set(Array.from({ length: 60 }, () => pickAvailableSite(fanBlade, n, today)));
  assert.ok(picks.size > 1, "pick should be random across runs");
  for (const p of picks) assert.ok(p && !DISRUPTION.affects(p));
});

test("other sites keep their own evidence", () => {
  const n = need(1);
  const pick = pickAvailableSite(fanBlade, n, today)!;
  const withPick = shortlist(n, pick);
  const without = shortlist(n, null);
  for (const a of withPick) {
    if (a.candidate.candidate_id === pick) continue;
    const b = without.find((x) => x.candidate.candidate_id === a.candidate.candidate_id)!;
    assert.equal(a.state, b.state, a.candidate.candidate_id);
  }
});
