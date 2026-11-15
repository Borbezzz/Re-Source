import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { AlertTriangle, ArrowRight, ChevronDown, Zap } from "lucide-react";
import { CHECK_ORDER, fmtDay, money, recommendationReason, type Assessed, type SourcingNeed } from "../data/checks.ts";
import { DISRUPTION } from "../data/sites.ts";
import { CheckIcon } from "./Checks.tsx";

const name = (a: Assessed) => a.candidate.supplier_name.replace(" (sample)", "");

export function DisruptionAlert({ recheck, affected, need }: { recheck: "idle" | "running" | "done"; affected: Assessed | null; need: SourcingNeed }) {
  return (
    <motion.div className="rs-alert" role="alert" initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }} style={{ left: 24, top: "auto", bottom: 64, transform: "none", width: "min(600px, calc(100% - var(--rs-drawer-w, 540px) - 72px))" }}>
      <span className="rs-alert-ico"><AlertTriangle size={18} /></span>
      <div style={{ display: "grid", gap: 4 }}>
        <b style={{ fontWeight: 550 }}>{DISRUPTION.title}</b>
        <span className="rs-small">
          {DISRUPTION.detail} {affected ? `Route ${affected.site.city} → Bristol now arrives ${fmtDay(affected.arrival)}; required ${fmtDay(need.requiredBy)}.` : ""}
        </span>
        <span className="rs-tiny">
          {DISRUPTION.source} · {new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })} · {recheck === "running" ? "rechecking affected criteria…" : "recheck complete"}
        </span>
      </div>
      {recheck === "running" ? <span className="rs-spinner" style={{ marginTop: 8 }} /> : <span className="rs-badge grad">Updated</span>}
    </motion.div>
  );
}

export function ShortlistDrawer({
  list,
  focusId,
  onFocus,
  need,
  disrupted,
  recheck,
  previousTop,
  invalidated,
  onDisrupt,
  onSelect,
  busy,
}: {
  list: Assessed[];
  focusId: string | null;
  onFocus: (id: string) => void;
  need: SourcingNeed;
  disrupted: boolean;
  recheck: "idle" | "running" | "done";
  previousTop: Assessed | null;
  invalidated: boolean;
  onDisrupt: () => void;
  onSelect: (id: string) => void;
  busy: boolean;
}) {
  const ranked = list.filter((a) => a.rank != null).sort((a, b) => a.rank! - b.rank!);
  const focus = list.find((a) => a.candidate.candidate_id === focusId) ?? ranked[0] ?? null;
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [othersOpen, setOthersOpen] = useState(false);
  const others = list.filter((a) => a.rank == null);
  const top = ranked[0];
  const prevNow = previousTop ? list.find((a) => a.candidate.candidate_id === previousTop.candidate.candidate_id) : null;
  const showCompare = disrupted && recheck === "done" && previousTop && top && previousTop.candidate.candidate_id !== top.candidate.candidate_id;

  return (
    <motion.aside className="rs-drawer" initial={{ x: 60, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }} aria-label="Recommended sites">
      <div className="rs-drawer-scroll">
        <AnimatePresence>
          {showCompare ? (
            <motion.section initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} style={{ display: "grid", gap: 10 }} aria-label="Updated recommendation">
              <h2 className="rs-h3">Recommendation updated</h2>
              <div className="rs-compare">
                <div>
                  <span className="rs-tiny">Previous</span>
                  <b style={{ fontWeight: 520 }}>{name(previousTop!)} · {previousTop!.site.city}</b>
                  <span className="rs-small" style={{ color: "var(--rs-bad)" }}>{prevNow?.state === "excluded" ? `Excluded from on-time shortlist: ${prevNow.reason}` : prevNow?.reason}</span>
                </div>
                <span style={{ alignSelf: "center", textAlign: "center", color: "var(--rs-text-2)" }}>→</span>
                <div className="is-new">
                  <span className="rs-tiny">New</span>
                  <b style={{ fontWeight: 520 }}>{name(top)} · {top.site.city}</b>
                  <span className="rs-small">{recommendationReason(top, list)} · est. {fmtDay(top.arrival)}</span>
                </div>
              </div>
              <p className="rs-tiny" style={{ margin: 0 }}>
                Rechecked: {DISRUPTION.rerun.join(" and ")} for {previousTop!.site.city} only. Part match, site and document evidence were retained. Requirements unchanged:{" "}
                <span className="rs-mono">{top.checks[0].note.split(" · ").slice(0, 2).join(" · ")}</span>, required by {fmtDay(need.requiredBy)}. Supplier confirmation still pending.
                {invalidated ? " Your earlier approval was invalidated and must be reviewed again." : ""}
              </p>
              <hr className="rs-divider" />
            </motion.section>
          ) : null}
        </AnimatePresence>

        <div style={{ display: "grid", gap: 10 }}>
          <h2 className="rs-h2">Recommended sites</h2>
          {ranked.length < 3 ? <span className="rs-tiny">{ranked.length} qualified site{ranked.length === 1 ? "" : "s"} — fewer than three is a valid result.</span> : null}
          <ul className="rs-rank-list">
            {ranked.map((a) => (
              <li key={a.candidate.candidate_id}>
                <motion.button layout type="button" className="rs-rank" aria-pressed={focus?.candidate.candidate_id === a.candidate.candidate_id} onClick={() => onFocus(a.candidate.candidate_id)}>
                  <span className="rs-rank-num">{a.rank}</span>
                  <span>
                    {name(a)} · {a.site.city}
                  </span>
                  <span className="rs-tiny">{fmtDay(a.arrival)}</span>
                </motion.button>
              </li>
            ))}
          </ul>
        </div>

        {focus ? (
          <section style={{ display: "grid", gap: 12 }} aria-label={`${name(focus)} details`}>
            <div>
              <h3 className="rs-h2" style={{ fontSize: 30 }}>{name(focus)}</h3>
              <div className="rs-small" style={{ fontSize: 15 }}>
                {focus.site.city}, {focus.candidate.country} · {focus.site.siteType}
              </div>
            </div>
            <div>
              <div className="rs-h3">
                {focus.rank === 1 ? recommendationReason(focus, list) : focus.rank ? `Ranked ${focus.rank} of ${ranked.length}` : focus.state === "excluded" ? "Excluded" : "Awaiting evidence"}
              </div>
              <div className="rs-small" style={{ fontSize: 14.5 }}>{focus.rank ? `${focus.checks[0].status === "pass" ? "Exact revision matched." : ""} Est. arrival ${fmtDay(focus.arrival)}.` : focus.reason}</div>
            </div>
            <table className="rs-table">
              <tbody>
                <tr>
                  <th>Part match</th>
                  <td className="rs-mono">{focus.checks[0].note}</td>
                </tr>
                <tr>
                  <th>Price</th>
                  <td>
                    {money(focus.candidate.price, focus.candidate.currency ?? "GBP")}
                    <span className="rs-tag-est">estimate</span>
                  </td>
                </tr>
                <tr>
                  <th>Estimated arrival</th>
                  <td>
                    {fmtDay(focus.arrival)} <span className="rs-small">· required {fmtDay(need.requiredBy)}</span>
                    {disrupted && DISRUPTION.affects(focus.candidate.candidate_id) ? <span className="rs-badge bad" style={{ marginLeft: 8 }}>Changed</span> : null}
                  </td>
                </tr>
                <tr>
                  <th>Availability</th>
                  <td>{focus.checks.find((c) => c.id === "availability")!.status === "pass" && !focus.available ? "Awaiting supplier confirmation" : focus.checks.find((c) => c.id === "availability")!.note}</td>
                </tr>
              </tbody>
            </table>
            <button type="button" className="rs-link rs-link-underline" style={{ fontSize: 15 }} aria-expanded={evidenceOpen} onClick={() => setEvidenceOpen((v) => !v)}>
              Evidence and qualification <ChevronDown size={16} style={{ transform: evidenceOpen ? "rotate(180deg)" : "none" }} />
            </button>
            <AnimatePresence initial={false}>
              {evidenceOpen ? (
                <motion.ul className="rs-checks" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} style={{ overflow: "hidden" }}>
                  {CHECK_ORDER.map((id) => {
                    const c = focus.checks.find((x) => x.id === id)!;
                    return (
                      <li key={id} className="rs-check-row" style={{ padding: "8px 0" }}>
                        <CheckIcon status={c.status} />
                        <span style={{ fontSize: 14 }}>{c.label}</span>
                        <span />
                        <small>{c.note}</small>
                      </li>
                    );
                  })}
                  <li className="rs-tiny" style={{ paddingTop: 6 }}>Source: {focus.site.sourceLabel}. Supplier claims stay unverified until documents arrive.</li>
                </motion.ul>
              ) : null}
            </AnimatePresence>
          </section>
        ) : null}

        <div>
          <button type="button" className="rs-link" style={{ fontSize: 14, color: "var(--rs-text-2)" }} aria-expanded={othersOpen} onClick={() => setOthersOpen((v) => !v)}>
            Not shortlisted ({others.length}) <ChevronDown size={15} style={{ transform: othersOpen ? "rotate(180deg)" : "none" }} />
          </button>
          {othersOpen ? (
            <ul className="rs-feed" style={{ marginTop: 10, maxHeight: "none" }}>
              {others.map((a) => (
                <li key={a.candidate.candidate_id}>
                  <CheckIcon status={a.state === "excluded" ? "fail" : a.state === "awaiting" ? "unknown" : "pass"} />
                  <button type="button" onClick={() => onFocus(a.candidate.candidate_id)} style={{ all: "unset", cursor: "pointer" }}>
                    {name(a)} · {a.site.city}
                  </button>
                  <span />
                  <small>{a.reason}</small>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        <p className="rs-tiny" style={{ margin: 0 }}>AI-assisted ranking from checked sources · prices are estimates until comparable supplier quotes arrive.</p>
      </div>
      <div className="rs-drawer-foot">
        {!disrupted ? (
          <button type="button" className="rs-btn rs-btn-ghost rs-btn-sm" onClick={onDisrupt} title="Inject a supplier disruption signal">
            <Zap size={14} /> Inject disruption
          </button>
        ) : (
          <span className="rs-tiny">Monitoring active</span>
        )}
        <button type="button" className="rs-btn rs-btn-solid" disabled={!focus || focus.rank == null || busy || recheck === "running"} onClick={() => focus && onSelect(focus.candidate.candidate_id)}>
          {busy ? "Preparing…" : "Select supplier"} <ArrowRight size={16} />
        </button>
      </div>
    </motion.aside>
  );
}
