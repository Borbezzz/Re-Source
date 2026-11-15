import { motion } from "motion/react";
import { ArrowRight, Ban, Check, CircleHelp } from "lucide-react";
import { CHECK_LABELS, CHECK_ORDER, type Assessed, type CheckStatus } from "../data/checks.ts";

export function CheckIcon({ status, running }: { status: CheckStatus | "pending"; running?: boolean }) {
  if (running) return <span className="rs-check-ico"><span className="rs-spinner" /></span>;
  if (status === "pass") return <span className="rs-check-ico pass"><Check size={14} strokeWidth={3} /></span>;
  if (status === "fail") return <span className="rs-check-ico fail"><Ban size={20} strokeWidth={1.8} /></span>;
  if (status === "unknown") return <span className="rs-check-ico unknown"><CircleHelp size={20} strokeWidth={1.8} /></span>;
  if (status === "info") return <span className="rs-check-ico" style={{ border: "1.5px solid var(--rs-text-2)", color: "var(--rs-text-2)", fontSize: 12 }}>£</span>;
  return <span className="rs-check-ico pending" />;
}

const stateBadge = (s: Assessed["state"]) =>
  s === "eligible" ? <span className="rs-badge ok">Eligible</span> : s === "awaiting" ? <span className="rs-badge wait">Awaiting evidence</span> : <span className="rs-badge bad">Excluded</span>;

export function CheckPanel({
  list,
  checked,
  checkingId,
  progress,
  focusId,
  onFocus,
  counts,
  total,
  onSkip,
  onDone,
}: {
  list: Assessed[];
  checked: Set<string>;
  checkingId: string | null;
  progress: Record<string, number>;
  focusId: string | null;
  onFocus: (id: string) => void;
  counts: { eligible: number; awaiting: number; excluded: number };
  total: number;
  onSkip: () => void;
  onDone: () => void;
}) {
  const focus = list.find((a) => a.candidate.candidate_id === focusId) ?? list[0];
  const step = focus ? (progress[focus.candidate.candidate_id] ?? 0) : 0;
  const allDone = checked.size === list.length && list.length > 0;
  const results = list.filter((a) => checked.has(a.candidate.candidate_id));
  return (
    <motion.section className="rs-check-panel rs-panel" initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }} aria-label="Supplier checks">
      <div style={{ display: "grid", gap: 8 }}>
        <h2 className="rs-h2">{allDone ? "Supplier checks complete" : "Checking supplier evidence"}</h2>
        <div className="rs-counts" aria-live="polite">
          <span><b>{total}</b> sites found</span>·<span><b>{counts.excluded}</b> excluded</span>·<span><b>{counts.awaiting}</b> awaiting evidence</span>·<span><b>{counts.eligible}</b> eligible</span>
        </div>
        <div className="rs-progress"><i style={{ width: `${(checked.size / Math.max(1, total)) * 100}%` }} /></div>
      </div>

      {focus ? (
        <div style={{ display: "grid", gap: 6 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10 }}>
            <span className="rs-h3">
              {focus.candidate.supplier_name.replace(" (sample)", "")} · {focus.site.city}
            </span>
            {checked.has(focus.candidate.candidate_id) ? stateBadge(focus.state) : <span className="rs-badge grad">Checking</span>}
          </div>
          <span className="rs-tiny">{focus.site.siteType} · checks apply to this site only</span>
          <ul className="rs-checks">
            {CHECK_ORDER.map((id, i) => {
              const res = focus.checks.find((c) => c.id === id)!;
              const done = checked.has(focus.candidate.candidate_id) || step > i + 1;
              const running = !done && step === i + 1 && checkingId === focus.candidate.candidate_id;
              return (
                <li key={id} className={`rs-check-row${running ? " is-running" : ""}`}>
                  <CheckIcon status={done ? res.status : "pending"} running={running} />
                  <span>{CHECK_LABELS[id]}</span>
                  <span />
                  {done ? <small>{res.note}</small> : null}
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      <hr className="rs-divider" />
      <ul className="rs-feed" aria-label="Results so far">
        {[...results].reverse().map((a) => (
          <li key={a.candidate.candidate_id}>
            <CheckIcon status={a.state === "eligible" ? "pass" : a.state === "excluded" ? "fail" : "unknown"} />
            <button type="button" onClick={() => onFocus(a.candidate.candidate_id)} style={{ all: "unset", cursor: "pointer" }}>
              {a.state === "excluded" ? "Site excluded" : a.state === "awaiting" ? "Awaiting verification" : "Eligible"} — {a.site.city}
            </button>
            <span className="rs-tiny">{a.site.sourceLabel}</span>
            <small>{a.reason}</small>
          </li>
        ))}
      </ul>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
        <span className="rs-tiny">Evidence and tool results shown; model reasoning is not.</span>
        {allDone ? (
          <button type="button" className="rs-btn rs-btn-grad" onClick={onDone}>
            Compare shortlist <ArrowRight size={16} />
          </button>
        ) : (
          <button type="button" className="rs-btn rs-btn-sm" onClick={onSkip}>
            Show all results
          </button>
        )}
      </div>
    </motion.section>
  );
}
