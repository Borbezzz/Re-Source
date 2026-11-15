import { useState } from "react";
import type { RiskEvidence, RiskPart } from "./types.ts";

export function EvidenceForm({ part, busy, onSave }: { part: RiskPart; busy: boolean; onSave: (evidence: RiskEvidence) => Promise<void> }) {
  const [kind, setKind] = useState<RiskEvidence["kind"]>("quote");
  const [error, setError] = useState<string | null>(null);
  return <form className="rs-risk-evidence-form" onSubmit={async (event) => {
    event.preventDefault(); setError(null);
    const form = event.currentTarget;
    const data = new FormData(form);
    const text = (key: string) => String(data.get(key) ?? "").trim();
    try {
      await onSave({ evidence_id: crypto.randomUUID(), part_id: part.part_id, kind,
        title: text("title"), excerpt: text("excerpt"), issued_on: text("issued_on"), source_url: text("source_url") || null,
        source_version: text("source_version") || "1", supplier: text("supplier") || null, part_number: text("part_number") || null,
        revision: text("revision") || null, quantity: text("quantity") ? Number(text("quantity")) : null,
        destination: text("destination") || null, route: text("route") || null, arrival_on: text("arrival_on") || null,
        event: text("event") || null, origin: "provided_document" });
      form.reset();
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save evidence."); }
  }}>
    <h3>Add dated evidence</h3>
    <p>Copy the source details. Clear any suggested field the document does not confirm; unknown fields stay unverified.</p>
    <label>Evidence type<select value={kind} onChange={(e) => setKind(e.target.value as RiskEvidence["kind"])}>
      <option value="quote">Supplier quote</option><option value="backorder">Supplier backorder</option><option value="shipment">Shipment update</option><option value="delivery">Delivery receipt</option><option value="route_disruption">Route disruption</option><option value="material_trend">Material trend</option><option value="freight_pressure">Freight pressure</option>
    </select></label>
    <label>Document title<input name="title" required maxLength={200} placeholder="Revised quote Q-1042" /></label>
    <div className="rs-risk-form-row"><label>Source date<input name="issued_on" type="date" required max={new Date().toISOString().slice(0,10)} /></label><label>Source version<input name="source_version" defaultValue="1" maxLength={100} /></label></div>
    <label>Source excerpt<textarea name="excerpt" required maxLength={4000} rows={4} placeholder="Paste the statement supporting this update." /></label>
    <label>Document URL (optional)<input name="source_url" type="url" maxLength={2000} placeholder="https://…" /></label>
    <div className="rs-risk-form-row"><label>Supplier<input name="supplier" maxLength={200} /></label><label>Arrival / receipt date<input name="arrival_on" type="date" /></label></div>
    <div className="rs-risk-form-row"><label>Part number in source<input name="part_number" defaultValue={part.part_number ?? ""} maxLength={150} /></label><label>Revision in source<input name="revision" defaultValue={part.revision ?? ""} maxLength={100} /></label></div>
    <div className="rs-risk-form-row"><label>Quantity covered<input name="quantity" type="number" min={1} max={1000000} defaultValue={part.need.quantity} /></label><label>Destination in source<input name="destination" defaultValue={part.need.destination} maxLength={200} /></label></div>
    <label>Shipping route (if documented)<input name="route" maxLength={200} placeholder="Use the same route name as the shipment record" /></label>
    <label>Event that changed the estimate<input name="event" maxLength={300} placeholder="Supplier revised dispatch after a backorder" /></label>
    <label className="rs-risk-check"><input type="checkbox" required />I checked these fields against the source document.</label>
    {error ? <p role="alert" className="rs-risk-error">{error}</p> : null}
    <button className="rs-btn rs-btn-grad" disabled={busy} type="submit">{busy ? "Saving and reassessing…" : "Save evidence and reassess"}</button>
  </form>;
}
