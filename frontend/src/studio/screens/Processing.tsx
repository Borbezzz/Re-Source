import { motion, AnimatePresence } from "motion/react";
import { Check, X } from "lucide-react";
import type { DesignPackage, StepId } from "../data/package.ts";
import type { ProductProject } from "../../product-flow/types.ts";

export interface StepState {
  status: "pending" | "running" | "done" | "error";
  detail?: string;
  at?: Date;
}
const LABELS: Record<StepId, string> = {
  read: "Read package",
  verify: "Verify file checksums",
  identify: "Identify assembly",
  map: "Map parts to geometry",
  link: "Link requirements",
  scene: "Prepare scene",
};

export function Processing({
  steps,
  pkg,
  project,
  error,
  busy,
  onConfirm,
  onRetry,
  solid,
}: {
  steps: Record<StepId, StepState>;
  pkg: DesignPackage | null;
  project: ProductProject | null;
  error: string | null;
  busy: boolean;
  onConfirm: () => void;
  onRetry: () => void;
  solid: number;
}) {
  const ready = pkg && project && steps.scene.status === "done";
  const done = Object.values(steps).filter((s) => s.status === "done").length;
  return (
    <div className="rs-ui-layer">
      <div className="rs-crumb rs-eyebrow">Workspace / Preparing assembly</div>
      <motion.section
        className="rs-process-panel rs-panel"
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: solid > 0.6 ? 0 : 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        aria-live="polite"
      >
        <div style={{ display: "grid", gap: 8 }}>
          <h1 className="rs-h2">{ready ? "Confirm extracted identity" : error ? "Package needs attention" : "Preparing assembly"}</h1>
          <div className="rs-progress" aria-hidden="true">
            <i style={{ width: `${(done / 6) * 100}%` }} />
          </div>
        </div>
        {ready ? (
          <details className="rs-small">
            <summary style={{ cursor: "pointer" }}>All 6 processing steps complete · checksums verified</summary>
          </details>
        ) : null}
        <ol className="rs-steps" hidden={!!ready}>
          {(Object.keys(LABELS) as StepId[]).map((id) => {
            const s = steps[id];
            return (
              <li key={id} className={`rs-step is-${s.status === "running" ? "active" : s.status}`}>
                <span className="rs-step-icon" aria-hidden="true">
                  {s.status === "done" ? (
                    <Check size={16} className="rs-check-ok" strokeWidth={2.4} />
                  ) : s.status === "running" ? (
                    <span className="rs-spinner" />
                  ) : s.status === "error" ? (
                    <X size={16} color="var(--rs-bad)" />
                  ) : (
                    <span style={{ width: 6, height: 6, borderRadius: 6, background: "var(--rs-text-3)" }} />
                  )}
                </span>
                <span>{LABELS[id]}</span>
                <span className="rs-step-time">{s.at ? s.at.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : ""}</span>
                {s.detail ? <span className="rs-step-detail">{s.detail}</span> : null}
              </li>
            );
          })}
        </ol>
        {error ? (
          <div style={{ display: "grid", gap: 12 }}>
            <p className="rs-intake-error" role="alert" style={{ margin: 0 }}>{error}</p>
            <button type="button" className="rs-btn" onClick={onRetry}>Choose another package</button>
          </div>
        ) : null}
        <AnimatePresence>
          {ready ? (
            <motion.div className="rs-confirm-card" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}>
              <hr className="rs-divider" />
              <dl className="rs-kv">
                <dt>Assembly</dt>
                <dd>{pkg.displayName}</dd>
                <dt>Package</dt>
                <dd className="rs-mono">{pkg.packageId} · v{pkg.packageVersion}</dd>
              </dl>
              {pkg.components.length > 0 ? <details className="rs-small rs-package-parts">
                <summary>{pkg.components.length} demo sourcing families across the assembly</summary>
                <ul>{pkg.components.map(c => <li key={c.componentId}>{c.name} · {c.assemblyQuantity} in assembly</li>)}</ul>
              </details> : null}
              <button type="button" className="rs-btn rs-btn-grad" onClick={onConfirm} disabled={busy}>
                {busy ? "Confirming…" : "Confirm and open assembly"}
              </button>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </motion.section>
    </div>
  );
}
