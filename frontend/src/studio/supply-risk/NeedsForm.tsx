import { useState } from "react";
import type { ProductProject } from "../../product-flow/types.ts";
import type { DesignPackage } from "../data/package.ts";
import type { NeedsDraft, RiskScan } from "./types.ts";
import "./supply-risk.css";

export function NeedsForm({ project, pkg, scan, busy, onConfirm }: {
  project: ProductProject; pkg?: DesignPackage; scan?: RiskScan | null; busy: boolean; onConfirm: (draft: NeedsDraft) => void;
}) {
  const [draft, setDraft] = useState<NeedsDraft>(() => ({
    destination: scan?.parts[0]?.need.destination ?? "", need_by: scan?.parts[0]?.need.need_by ?? "",
    parts: project.parts.map((p) => {
      const c = pkg?.components.find((c) => c.componentId.toLowerCase() === p.part_id);
      return { part_id: p.part_id, part_number: c?.partNumber ?? p.part_number ?? "", revision: c?.revision ?? p.requirements.find((r) => r.key === "revision")?.value ?? "", quantity: scan?.parts.find((s) => s.part_id === p.part_id)?.need.quantity ?? p.quantity };
    }),
  }));
  const update = (id: string, value: Partial<NeedsDraft["parts"][number]>) => setDraft((d) => ({ ...d, parts: d.parts.map((p) => p.part_id === id ? { ...p, ...value } : p) }));
  return <form className="rs-risk-needs" onSubmit={(e) => { e.preventDefault(); onConfirm(draft); }}>
    <h3>What does this project need?</h3>
    <p>Review the extracted identity and purchase quantity. Missing part numbers or revisions remain broader exposure until you confirm them.</p>
    <div className="rs-risk-needs-parts">{draft.parts.map((p) => <fieldset key={p.part_id} disabled={busy}>
      <legend>{project.parts.find((part) => part.part_id === p.part_id)?.name}</legend>
      <label>Part number<input value={p.part_number} placeholder="Not yet identified" onChange={(e) => update(p.part_id, { part_number: e.target.value })} maxLength={150} /></label>
      <label>Revision<input value={p.revision} placeholder="Unknown" onChange={(e) => update(p.part_id, { revision: e.target.value })} maxLength={100} /></label>
      <label>Purchase quantity<input type="number" min={1} max={1000000} required value={p.quantity} onChange={(e) => update(p.part_id, { quantity: e.target.valueAsNumber })} /></label>
    </fieldset>)}</div>
    <div className="rs-risk-form-row">
      <label>Delivery destination<input required minLength={2} maxLength={200} value={draft.destination} disabled={busy} placeholder="City, country or receiving site" onChange={(e) => setDraft({ ...draft, destination: e.target.value })} /></label>
      <label>Need-by date<input type="date" required value={draft.need_by} disabled={busy} onChange={(e) => setDraft({ ...draft, need_by: e.target.value })} /></label>
    </div>
    <p className="rs-risk-note">Confirming starts the scan. Public news stays on the watchlist until it matches a documented dependency.</p>
    <button type="submit" className="rs-btn rs-btn-grad" disabled={busy}>{busy ? "Confirming and scanning…" : "Confirm parts and scan supply risk"}</button>
  </form>;
}
