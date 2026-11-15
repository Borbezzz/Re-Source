import { motion } from "motion/react";
import { Check, CircleHelp, Clock, RotateCcw } from "lucide-react";
import type { PackageComponent } from "../data/package.ts";
import type { Assessed } from "../data/checks.ts";
import type { ProductProject } from "../../product-flow/types.ts";
import type { ReassemblyPhase } from "../scene/EngineCanvas.tsx";

export function ReturnPanel({
  component,
  project,
  chosen,
  phase,
  onReplay,
  onAssembly,
  onNew,
}: {
  component: PackageComponent;
  project: ProductProject;
  chosen: Assessed | null;
  phase: ReassemblyPhase;
  onReplay: () => void;
  onAssembly: () => void;
  onNew: () => void;
}) {
  const supplier = chosen?.candidate.supplier_name.replace(" (sample)", "") ?? "selected supplier";
  const events = [...project.events].reverse().slice(0, 6);
  return (
    <div className="rs-ui-layer">
      <div className="rs-crumb rs-eyebrow">Assembly / Reassembly preview</div>
      <motion.section className="rs-return-panel rs-panel" initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }} aria-live="polite">
        <div style={{ display: "grid", gap: 6 }}>
          <span className="rs-eyebrow">{phase === "done" ? "Replacement matched" : phase === "remove" ? "Removing faulty part" : phase === "insert" ? "Inserting replacement" : "Preparing preview"}</span>
          <h1 className="rs-h2">Reassembly preview</h1>
          <p className="rs-small" style={{ margin: 0 }}>
            {component.name} from {supplier}. A visual preview — not a functional test or proof of compatibility.
          </p>
        </div>
        <div>
          <div className="rs-state">
            <span className="rs-check-ico pass"><Check size={14} strokeWidth={3} /></span>
            <div>
              <b>Replacement identity</b>
              <p className="rs-mono">{component.partNumber} · Rev {component.revision} matched to the supplier offer (supplier claim).</p>
            </div>
          </div>
          <div className="rs-state">
            <span className="rs-check-ico unknown"><CircleHelp size={20} /></span>
            <div>
              <b>Engineering acceptance · not established</b>
              <p>Waiting for supplier release certificate and traceability records, then the applicable human acceptance.</p>
            </div>
          </div>
          <div className="rs-state">
            <span className="rs-check-ico" style={{ color: "var(--rs-amber)" }}><Clock size={18} /></span>
            <div>
              <b>Procurement · quote confirmed (simulated)</b>
              <p>{project.package?.receipt ? `Receipt ${project.package.receipt}. ` : ""}Order not committed. Dispatch not confirmed.</p>
            </div>
          </div>
        </div>
        <details>
          <summary className="rs-small" style={{ cursor: "pointer" }}>Case history ({project.events.length} events)</summary>
          <ul className="rs-feed" style={{ marginTop: 10 }}>
            {events.map((e) => (
              <li key={e.sequence} style={{ gridTemplateColumns: "1fr" }}>
                <span className="rs-small" style={{ color: "var(--rs-text)" }}>{e.summary}</span>
                <span className="rs-tiny">{new Date(e.created_at).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })} · {e.type}</span>
              </li>
            ))}
          </ul>
        </details>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button type="button" className="rs-btn rs-btn-grad" onClick={onAssembly}>Back to assembly</button>
          <button type="button" className="rs-btn" onClick={onReplay}><RotateCcw size={14} /> Replay</button>
          <button type="button" className="rs-btn rs-btn-ghost" onClick={onNew}>New case</button>
        </div>
      </motion.section>
    </div>
  );
}
