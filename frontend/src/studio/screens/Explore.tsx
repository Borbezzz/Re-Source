import { useId, useState } from "react";
import { motion } from "motion/react";
import { ArrowLeft, ArrowRight, ChevronDown, Expand, Minimize2, RefreshCcw, RotateCw, X } from "lucide-react";
import type { PackageComponent, RequirementSet } from "../data/package.ts";
import type { SourcingNeed } from "../data/checks.ts";
import { ComponentThumb } from "../scene/ComponentThumb.tsx";
import { DESTINATION } from "../data/sites.ts";

const MAX_PURCHASE_QUANTITY = 100;

export function ComponentsPanel({ components, selected, onSelect }: { components: PackageComponent[]; selected: string | null; onSelect: (id: string) => void }) {
  const [open, setOpen] = useState(true);
  const ordered = [...components].sort((a, b) => (a.role === "primary" ? -1 : b.role === "primary" ? 1 : 0));
  return (
    <motion.aside
      className={`rs-components${open ? "" : " is-collapsed"}`}
      aria-label="Components"
      initial={{ opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.7, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
      style={{ bottom: open ? 24 : "auto" }}
    >
      <button type="button" className="rs-components-head" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        Components <ChevronDown size={18} />
      </button>
      {open ? (
        <>
          <ul className="rs-comp-list">
            {ordered.map((c) => (
              <li key={c.componentId}>
                <button type="button" className="rs-comp" aria-pressed={selected === c.componentId} onClick={() => onSelect(c.componentId)}>
                  <span className="rs-comp-ring" aria-hidden="true" />
                  <span>{c.name}</span>
                  <span className="rs-comp-sub rs-mono">
                    {c.partNumber} · Rev {c.revision}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <p className="rs-tiny" style={{ marginTop: "auto", paddingTop: 18 }}>
            Select a part in the list or on the model. Assembly quantities differ from purchase quantities.
          </p>
        </>
      ) : null}
    </motion.aside>
  );
}

export function SceneControls({ spin, exploded, onSpin, onExplode, onReset }: { spin: boolean; exploded: boolean; onSpin: () => void; onExplode: () => void; onReset: () => void }) {
  return (
    <motion.div className="rs-scene-controls" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}>
      <button type="button" className={`rs-btn${spin ? " is-active" : ""}`} aria-pressed={spin} onClick={onSpin}>
        <RotateCw size={15} /> Rotate
      </button>
      <button type="button" className={`rs-btn${exploded ? " is-active" : ""}`} aria-pressed={exploded} onClick={onExplode}>
        {exploded ? <Minimize2 size={15} /> : <Expand size={15} />} {exploded ? "Assemble" : "Explode"}
      </button>
      <button type="button" className="rs-btn" onClick={onReset}>
        <RefreshCcw size={15} /> Reset view
      </button>
    </motion.div>
  );
}

export function ContextCard({
  glbUrl,
  component,
  requirement,
  mode,
  need,
  onNeed,
  onStart,
  onBack,
  onClose,
  onSubmit,
  busy,
}: {
  glbUrl: string;
  component: PackageComponent;
  requirement: RequirementSet;
  mode: "context" | "need";
  need: SourcingNeed;
  onNeed: (n: SourcingNeed) => void;
  onStart: (reason: SourcingNeed["reason"]) => void;
  onBack: () => void;
  onClose: () => void;
  onSubmit: () => void;
  busy: boolean;
}) {
  const today = new Date().toISOString().slice(0, 10);
  const quantityId = useId();
  const [quantity, setQuantity] = useState(() => String(need.quantity));
  const quantityValue = Number(quantity);
  const quantityError = quantity === "" || !Number.isFinite(quantityValue) || quantityValue < 1
    ? "Quantity must be at least 1."
    : !Number.isInteger(quantityValue)
      ? "Quantity must be a whole number."
      : quantityValue > MAX_PURCHASE_QUANTITY
        ? `Quantity must be at most ${MAX_PURCHASE_QUANTITY}.`
        : null;
  return (
    <motion.section
      layoutId="component-card"
      className="rs-context rs-panel"
      aria-label={`${component.name} actions`}
      initial={{ opacity: 0, x: -18 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -18 }}
      transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
    >
      <div style={{ display: "grid", gridTemplateColumns: "76px 1fr auto", gap: 14, alignItems: "center" }}>
        <ComponentThumb url={glbUrl} nodeIds={component.nodeIds} label={component.name} />
        <div>
          <div className="rs-anchor-title">{component.name}</div>
          <div className="rs-anchor-sub rs-mono">
            {component.partNumber} · Rev {component.revision}
          </div>
        </div>
        <button type="button" className="rs-btn rs-btn-ghost rs-btn-sm" onClick={onClose} aria-label="Clear selection">
          <X size={16} />
        </button>
      </div>
      {mode === "context" ? (
        <>
          <dl className="rs-kv">
            <dt>In assembly</dt>
            <dd>
              {component.assemblyQuantity} × in {component.parentAssemblyId}
            </dd>
            <dt>Requirements</dt>
            <dd>
              {requirement.id} · {requirement.mandatoryChecks.length} mandatory checks
            </dd>
            <dt>Condition</dt>
            <dd style={{ textTransform: "capitalize" }}>{requirement.condition}</dd>
          </dl>
          <div className="rs-context-actions">
            <button type="button" className="rs-choice" onClick={() => onStart("faulty")}>
              Replace faulty part
              <small>Source the same approved part and revision</small>
              <ArrowRight size={17} />
            </button>
            <button type="button" className="rs-choice" onClick={() => onStart("supplier")}>
              Change supplier
              <small>Find another qualified supplying site</small>
              <ArrowRight size={17} />
            </button>
          </div>
        </>
      ) : (
        <form
          className="rs-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (quantityError || busy) return;
            onSubmit();
          }}
        >
          <div className="rs-field">
            <span>Reason</span>
            <div className="rs-seg" role="group" aria-label="Reason">
              <button type="button" aria-pressed={need.reason === "faulty"} onClick={() => onNeed({ ...need, reason: "faulty" })}>
                Faulty part
              </button>
              <button type="button" aria-pressed={need.reason === "supplier"} onClick={() => onNeed({ ...need, reason: "supplier" })}>
                Change supplier
              </button>
            </div>
          </div>
          <div className="rs-row">
            <div className="rs-field">
              <label htmlFor={quantityId}>Quantity</label>
              <input
                id={quantityId}
                className="rs-input"
                type="number"
                min={1}
                max={MAX_PURCHASE_QUANTITY}
                step={1}
                required
                value={quantity}
                aria-invalid={Boolean(quantityError)}
                aria-describedby={quantityError ? `${quantityId}-error` : undefined}
                onChange={(e) => {
                  setQuantity(e.target.value);
                  const value = e.target.valueAsNumber;
                  if (Number.isInteger(value) && value >= 1 && value <= MAX_PURCHASE_QUANTITY) {
                    onNeed({ ...need, quantity: value });
                  }
                }}
              />
              {quantityError ? <small className="rs-field-error" id={`${quantityId}-error`} role="alert">{quantityError}</small> : null}
            </div>
            <label className="rs-field">
              <span>Required on site by</span>
              <input className="rs-input" type="date" min={today} value={need.requiredBy} onChange={(e) => e.target.value && onNeed({ ...need, requiredBy: e.target.value })} required />
            </label>
          </div>
          <label className="rs-field">
            <span>Delivery site</span>
            <input className="rs-input" value={DESTINATION.site} readOnly aria-describedby="dest-note" />
          </label>
          <label className="rs-field">
            <span>Budget (optional)</span>
            <input className="rs-input" inputMode="numeric" placeholder="No limit" value={need.budget ?? ""} onChange={(e) => onNeed({ ...need, budget: e.target.value ? Number(e.target.value.replace(/\D/g, "")) || null : null })} />
          </label>
          <p className="rs-note" id="dest-note">
            Sourcing the exact approved part: <span className="rs-mono">{component.partNumber} Rev {component.revision}</span>, {requirement.condition}. Manufacture-to-specification or substitution needs extra evidence and acceptance, so it isn't offered here.
          </p>
          <div style={{ display: "flex", gap: 10, justifyContent: "space-between" }}>
            <button type="button" className="rs-btn rs-btn-ghost" onClick={onBack}>
              <ArrowLeft size={15} /> Back
            </button>
            <button type="submit" className="rs-btn rs-btn-grad" disabled={busy || Boolean(quantityError)}>
              {busy ? "Starting…" : "Find suppliers"} <ArrowRight size={16} />
            </button>
          </div>
        </form>
      )}
    </motion.section>
  );
}
