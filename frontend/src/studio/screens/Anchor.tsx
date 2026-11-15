import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ChevronDown, Undo2 } from "lucide-react";
import type { PackageComponent } from "../data/package.ts";
import { fmtDay, money, type SourcingNeed } from "../data/checks.ts";
import { ComponentThumb } from "../scene/ComponentThumb.tsx";
import { DESTINATION } from "../data/sites.ts";

/** Persistent selected-part anchor: same asset, identity and request through map stages. */
export function AnchorCard({ glbUrl, component, need, onReturn, status }: { glbUrl: string; component: PackageComponent; need: SourcingNeed; onReturn: () => void; status?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <motion.section layoutId="component-card" className="rs-anchor rs-panel" transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }} aria-label="Selected component">
      <button type="button" className="rs-anchor-head" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        <ComponentThumb url={glbUrl} nodeIds={component.nodeIds} label={component.name} />
        <span>
          <span className="rs-anchor-title" style={{ display: "block" }}>{component.name}</span>
          <span className="rs-anchor-sub rs-mono" style={{ display: "block" }}>
            {component.partNumber} · Rev {component.revision}
          </span>
          {status ? <span className="rs-tiny" style={{ display: "block", marginTop: 3 }}>{status}</span> : null}
        </span>
        <ChevronDown size={17} style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform .3s", color: "var(--rs-text-2)" }} />
      </button>
      <AnimatePresence initial={false}>
        {open ? (
          <motion.div className="rs-anchor-body" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}>
            <dl className="rs-kv">
              <dt>Reason</dt>
              <dd>{need.reason === "faulty" ? "Replace faulty part" : "Change supplier"}</dd>
              <dt>Quantity</dt>
              <dd>{need.quantity}</dd>
              <dt>Required by</dt>
              <dd>{fmtDay(need.requiredBy)}</dd>
              <dt>Deliver to</dt>
              <dd>{DESTINATION.name}</dd>
              <dt>Budget</dt>
              <dd>{need.budget ? money(need.budget) : "Not set"}</dd>
            </dl>
            <button type="button" className="rs-btn rs-btn-sm" onClick={onReturn}>
              <Undo2 size={14} /> Return to engine
            </button>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </motion.section>
  );
}
