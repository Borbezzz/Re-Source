import type { ProductCandidate } from "../../product-flow/types.ts";
import { DISRUPTION, SITES, type SiteFixture } from "./sites.ts";

export type CheckId = "identity" | "site" | "documents" | "availability" | "arrival" | "commercial";
export type CheckStatus = "pass" | "fail" | "unknown" | "info";
export interface CheckResult {
  id: CheckId;
  label: string;
  status: CheckStatus;
  note: string;
}
export type CandidateState = "eligible" | "awaiting" | "excluded";
export interface SourcingNeed {
  reason: "faulty" | "supplier";
  quantity: number;
  requiredBy: string; // yyyy-mm-dd
  destination: string;
  budget: number | null;
}
export interface Assessed {
  candidate: ProductCandidate;
  site: SiteFixture;
  checks: CheckResult[];
  state: CandidateState;
  reason: string; // headline for excluded/awaiting
  arrival: Date;
  dispatchDays: number;
  /** Demo: this site's stock is shown as confirmed available. */
  available: boolean;
  score: number;
  rank: number | null;
}

export const CHECK_LABELS: Record<CheckId, string> = {
  identity: "Part and revision match",
  site: "Site qualification",
  documents: "Document evidence",
  availability: "Availability",
  arrival: "Arrival feasibility",
  commercial: "Commercial comparison",
};
export const CHECK_ORDER: CheckId[] = ["identity", "site", "documents", "availability", "arrival", "commercial"];

const DAY = 86_400_000;
export const addDays = (d: Date, n: number) => new Date(d.getTime() + n * DAY);
export const isoDay = (d: Date) => d.toISOString().slice(0, 10);
export const fmtDay = (d: Date | string) =>
  new Date(typeof d === "string" ? `${d}T12:00:00` : d).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
export const money = (n: number | null | undefined, cur = "GBP") =>
  n == null ? "—" : new Intl.NumberFormat("en-GB", { style: "currency", currency: cur, maximumFractionDigits: 0 }).format(n);

export function defaultNeed(today = new Date()): SourcingNeed {
  return { reason: "faulty", quantity: 1, requiredBy: isoDay(addDays(today, 14)), destination: "Filton, Bristol", budget: null };
}

/** Evaluate one candidate. Every check is per-candidate; a pass here is not a global pass. */
export function assess(
  candidate: ProductCandidate,
  required: { partNumber: string; revision: string; condition: string },
  need: SourcingNeed,
  opts: { today?: Date; disrupted?: boolean; availableSite?: string | null } = {},
): Assessed | null {
  const fixture = SITES[candidate.candidate_id];
  if (!fixture) return null;
  const today = opts.today ?? new Date();
  const available = candidate.candidate_id === opts.availableSite;
  const site = available ? availableFixture(fixture, candidate, need, today) : fixture;
  const disruption = opts.disrupted && DISRUPTION.affects(candidate.candidate_id) ? DISRUPTION.extraDispatchDays : 0;
  const dispatchDays = (candidate.lead_time_days ?? 7) + disruption;
  const arrival = addDays(today, dispatchDays + site.transitDays);
  const requiredBy = new Date(`${need.requiredBy}T23:59:00`);
  const checks: CheckResult[] = [];

  const offeredPn = site.offeredPartNumber ?? required.partNumber;
  const offeredRev = site.offeredRevision ?? required.revision;
  const offeredCond = site.offeredCondition ?? "New";
  checks.push(
    offeredPn !== required.partNumber
      ? { id: "identity", label: CHECK_LABELS.identity, status: "fail", note: `${offeredPn} offered; ${required.partNumber} required` }
      : offeredRev !== required.revision
        ? { id: "identity", label: CHECK_LABELS.identity, status: "fail", note: `Revision ${offeredRev} offered; Revision ${required.revision} required` }
        : offeredCond.toLowerCase() !== required.condition.toLowerCase()
          ? { id: "identity", label: CHECK_LABELS.identity, status: "fail", note: `${offeredCond} unit offered; ${required.condition} required` }
          : { id: "identity", label: CHECK_LABELS.identity, status: "pass", note: `${required.partNumber} · Rev ${required.revision} · ${offeredCond}` },
  );
  checks.push(
    site.siteEvidence === "provided"
      ? { id: "site", label: CHECK_LABELS.site, status: "pass", note: `${site.siteType} evidence on file` }
      : { id: "site", label: CHECK_LABELS.site, status: "unknown", note: "Awaiting evidence for the supplying site" },
  );
  const missingDocs = [site.applicability === "missing" && "applicability", site.traceability === "missing" && "traceability"].filter(Boolean);
  checks.push(
    missingDocs.length
      ? { id: "documents", label: CHECK_LABELS.documents, status: "unknown", note: `Awaiting ${missingDocs.join(" and ")} records` }
      : { id: "documents", label: CHECK_LABELS.documents, status: "pass", note: "Applicability and traceability documents listed" },
  );
  checks.push(
    site.stock == null
      ? { id: "availability", label: CHECK_LABELS.availability, status: "unknown", note: "Stock not confirmed by supplier" }
      : site.stock < need.quantity
        ? { id: "availability", label: CHECK_LABELS.availability, status: "fail", note: `${site.stock} available; ${need.quantity} needed` }
        : {
            id: "availability",
            label: CHECK_LABELS.availability,
            status: disruption ? "unknown" : "pass",
            note: disruption ? "Stock held; release date pending supplier update" : available ? `${site.stock} in stock · available now` : `${site.stock} in stock · supplier claim, unconfirmed`,
          },
  );
  checks.push(
    arrival <= requiredBy
      ? { id: "arrival", label: CHECK_LABELS.arrival, status: "pass", note: `Est. ${fmtDay(arrival)} · required by ${fmtDay(need.requiredBy)}` }
      : { id: "arrival", label: CHECK_LABELS.arrival, status: "fail", note: `Est. ${fmtDay(arrival)} · misses required ${fmtDay(need.requiredBy)}` },
  );
  const price = candidate.price ?? null;
  checks.push({
    id: "commercial",
    label: CHECK_LABELS.commercial,
    status: "info",
    note:
      price == null
        ? "No price yet"
        : need.budget && price * need.quantity > need.budget
          ? `${money(price, candidate.currency ?? "GBP")} estimate · above budget, ranked lower`
          : `${money(price, candidate.currency ?? "GBP")} estimate · awaiting quote`,
  });

  const fail = checks.find((c) => c.status === "fail");
  const unknown = checks.find((c) => c.status === "unknown");
  const state: CandidateState = fail ? "excluded" : unknown ? "awaiting" : "eligible";
  return {
    candidate,
    site,
    checks,
    state,
    reason: fail ? fail.note : unknown ? unknown.note : "All mandatory checks passed",
    arrival,
    dispatchDays,
    available,
    score: 0,
    rank: null,
  };
}

/**
 * Demo: the site chosen for this search run presents full evidence, enough stock
 * for the requested quantity and the exact part/revision/condition, and ships
 * quickly enough to arrive by the required date where its dispatch time allows.
 */
function availableFixture(site: SiteFixture, candidate: ProductCandidate, need: SourcingNeed, today: Date): SiteFixture {
  const requiredBy = new Date(`${need.requiredBy}T23:59:00`);
  const window = Math.floor((requiredBy.getTime() - today.getTime()) / DAY) - (candidate.lead_time_days ?? 7);
  const { offeredPartNumber: _pn, offeredRevision: _rev, offeredCondition: _cond, ...rest } = site;
  return {
    ...rest,
    applicability: "provided",
    traceability: "provided",
    siteEvidence: "provided",
    stock: Math.max(site.stock ?? 0, need.quantity),
    transitDays: Math.max(1, Math.min(site.transitDays, window)),
  };
}

/**
 * Demo: choose one site per search run to show as available. Prefers sites whose
 * dispatch time can still meet the required date, and never the site the
 * simulated disruption targets, so the disruption story still changes the ranking.
 */
export function pickAvailableSite(candidates: ProductCandidate[], need: SourcingNeed, today = new Date()): string | null {
  const known = candidates.filter((c) => SITES[c.candidate_id] && !DISRUPTION.affects(c.candidate_id));
  if (!known.length) return null;
  const requiredBy = new Date(`${need.requiredBy}T23:59:00`).getTime();
  const fits = known.filter((c) => today.getTime() + ((c.lead_time_days ?? 7) + 1) * DAY <= requiredBy);
  const pool = fits.length ? fits : [...known].sort((a, b) => (a.lead_time_days ?? 7) - (b.lead_time_days ?? 7)).slice(0, 1);
  return pool[Math.floor(Math.random() * pool.length)].candidate_id;
}

/** Rank eligible candidates: speed 0.5, cost 0.35 (budget preference), evidence 0.15. */
export function rankAll(list: Assessed[], need: SourcingNeed, pinned: string | null = null): Assessed[] {
  const eligible = list.filter((a) => a.state === "eligible");
  const minPrice = Math.min(...eligible.map((a) => a.candidate.price ?? Infinity));
  const requiredBy = new Date(`${need.requiredBy}T23:59:00`).getTime();
  for (const a of list) {
    if (a.state !== "eligible") {
      a.score = 0;
      a.rank = null;
      continue;
    }
    const margin = Math.max(0, (requiredBy - a.arrival.getTime()) / DAY);
    const speed = Math.min(1, margin / 14);
    let cost = a.candidate.price ? minPrice / a.candidate.price : 0;
    if (need.budget && (a.candidate.price ?? 0) * need.quantity > need.budget) cost *= 0.5;
    a.score = Math.round((0.5 * speed + 0.35 * cost + 0.15) * 1000) / 10;
  }
  eligible.sort((x, y) => y.score - x.score || x.arrival.getTime() - y.arrival.getTime());
  // Demo: the available site always makes the recommended list (it takes the last slot if needed).
  const pinnedAt = pinned ? eligible.findIndex((a) => a.candidate.candidate_id === pinned) : -1;
  if (pinnedAt > 2) eligible.splice(2, 0, ...eligible.splice(pinnedAt, 1));
  eligible.slice(0, 3).forEach((a, i) => (a.rank = i + 1));
  eligible.slice(3).forEach((a) => (a.rank = null));
  return list;
}

export function recommendationReason(top: Assessed, list: Assessed[]): string {
  const ranked = list.filter((a) => a.rank != null);
  const fastest = ranked.every((a) => a.arrival >= top.arrival);
  const cheapest = ranked.every((a) => (a.candidate.price ?? Infinity) >= (top.candidate.price ?? Infinity));
  if (fastest && cheapest) return "Recommended for delivery fit and cost";
  if (fastest) return "Recommended for delivery fit";
  if (cheapest) return "Recommended for cost";
  return "Recommended for overall balance";
}

export function counts(list: Assessed[]) {
  return {
    total: list.length,
    eligible: list.filter((a) => a.state === "eligible").length,
    awaiting: list.filter((a) => a.state === "awaiting").length,
    excluded: list.filter((a) => a.state === "excluded").length,
  };
}
