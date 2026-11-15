import { useState } from "react";
import { ArrowRight, FileText, RefreshCw, X } from "lucide-react";
import { ArrivalTimeline } from "./ArrivalTimeline.tsx";
import { EvidenceForm } from "./EvidenceForm.tsx";
import { dateLabel, RISK_LABELS, type RiskEvidence, type RiskObservation, type RiskPart, type RiskScan } from "./types.ts";
import "./supply-risk.css";

function SourcePreviews({ scan }: { scan: RiskScan }) {
  return <section className="rs-risk-sources" aria-label="Public news and data watchlist">
    <h3>Public news & data watchlist</h3>
    <p>These sources describe wider conditions. They do not establish a delay for your part.</p>
    <div className="rs-risk-providers">{scan.providers.map((p) => <span key={p.name}>{p.name}: {p.status === "searched" ? `${p.source_count} sources found` : p.status === "unavailable" ? "temporarily unavailable" : "not connected"}</span>)}</div>
    {!scan.sources.length ? <p>Public source previews appear after the web search completes. Part evidence is assessed independently.</p> : null}
    {scan.sources.map((source) => <article className="rs-risk-source" key={source.url}>
      <div className="rs-risk-source-meta"><span>{source.publisher}</span><span>{source.provider === "Reference" ? "Reference dataset" : "Search preview"}</span></div>
      <a href={source.url} target="_blank" rel="noreferrer">{source.title}<ArrowRight size={15} /></a>
      <p>{source.excerpt}</p>
      <small>{source.published_on ? `Published ${source.published_on.slice(0, 10)} · ` : "Publication date not supplied · "}{source.provider === "Reference" ? "Reference added" : "Retrieved"} {dateLabel(source.retrieved_at)}</small>
    </article>)}
  </section>;
}

export function RiskOverview({ scan, busy, error, onSelect, onRefresh, onEdit }: {
  scan: RiskScan; busy: boolean; error: string | null; onSelect: (id: string) => void; onRefresh: () => void; onEdit: () => void;
}) {
  const atRisk = scan.parts.filter((p) => p.status === "at_risk").length;
  return <section className="rs-risk-overview rs-panel" aria-label="Supply-risk scan">
    <div className="rs-risk-heading"><h2>Will the parts arrive in time?</h2><button className="rs-btn rs-btn-ghost rs-btn-sm" aria-label="Refresh public risk sources" disabled={busy} onClick={onRefresh}><RefreshCw size={17} /></button></div>
    <p>{scan.status === "needs_confirmation" ? "Requirements changed. Confirm them again before relying on this scan." : atRisk ? `${atRisk} part${atRisk === 1 ? "" : "s"} with matched delivery risk. Select one to review the evidence and next steps.` : "Scan complete. Review each part’s delivery evidence; unknown arrival is not a clean bill of health."}</p>
    <div className="rs-risk-part-rows">{scan.parts.map((part) => <button key={part.part_id} onClick={() => onSelect(part.part_id)}><span><strong>{part.name}</strong><small>{part.need.quantity} required · need by {dateLabel(part.need.need_by)}</small></span><span className={`rs-risk-status is-${part.status}`}>{RISK_LABELS[part.status]}</span></button>)}</div>
    <button className="rs-btn rs-btn-ghost rs-btn-sm" onClick={onEdit}>Edit project needs</button>
    {busy ? <p role="status">Checking Tavily and Linkup for public context…</p> : null}
    {error ? <p role="alert" className="rs-risk-error">{error}</p> : null}
    <SourcePreviews scan={scan} />
  </section>;
}

export function RiskPanel({ part, scan, busy, error, onClose, onFind, onSave, onRefresh, onEdit }: {
  part: RiskPart; scan: RiskScan; busy: boolean; error: string | null; onClose: () => void; onFind: () => void;
  onSave: (evidence: RiskEvidence) => Promise<void>; onRefresh: () => void; onEdit: () => void;
}) {
  const [adding, setAdding] = useState(false);
  const [example, setExample] = useState(false);
  const alternatives = part.observations.filter((o) => o.evidence.kind === "quote" && o.evidence.arrival_on && o.evidence.arrival_on <= part.need.need_by && o.level !== "superseded");
  return <section className="rs-risk-panel rs-panel" aria-label={`${part.name} supply risk`}>
    <div className="rs-risk-heading"><h2>{part.name}</h2><button className="rs-btn rs-btn-ghost rs-btn-sm" onClick={onClose} aria-label="Close part risk panel"><X size={18} /></button></div>
    <p className="rs-risk-identity">{part.part_number ?? "Part number unknown"} · Rev {part.revision ?? "unknown"} · {part.need.quantity} required</p>
    <span className={`rs-risk-status is-${part.status}`}>{RISK_LABELS[part.status]}</span>
    <p className="rs-risk-summary">{part.summary}</p>
    <dl className="rs-risk-deadline"><div><dt>Need by</dt><dd>{dateLabel(part.need.need_by)} {part.need.need_by.slice(0, 4)}</dd></div><div><dt>Destination</dt><dd>{part.need.destination}</dd></div></dl>
    {scan.status === "needs_confirmation" ? <p className="rs-risk-error" role="alert">Requirements changed. This assessment needs reconfirmation. <button onClick={onEdit}>Review needs</button></p> : null}
    <div className="rs-risk-actions"><button className="rs-btn" onClick={(event) => event.currentTarget.closest("section")?.querySelector("#risk-timeline")?.scrollIntoView({ block: "start" })}>View quote and timeline</button><button className="rs-btn rs-btn-grad" onClick={onFind}>Find alternative suppliers <ArrowRight size={15} /></button></div>
    <div id="risk-timeline"><ArrivalTimeline observations={part.observations} deadline={part.need.need_by} /></div>
    {part.missing.length ? <div className="rs-risk-missing"><h3>Details still needed</h3><p>{part.missing.join(" · ")}</p><button className="rs-btn rs-btn-ghost rs-btn-sm" onClick={onEdit}>Review part identity and needs</button></div> : null}
    {part.exposure.length ? <section><h3>Broader exposure</h3><p>{part.exposure.join(" · ")}</p><p>Confirm the specific part and supplier to connect these exposures to delivery.</p></section> : null}
    <section className="rs-risk-next"><h3>What can I do about it?</h3><ul>{part.actions.map((action) => <li key={action}>{action}</li>)}</ul>
      {alternatives.length ? <div className="rs-risk-alternatives">{alternatives.map((o) => <p key={o.evidence.evidence_id}><strong>{o.evidence.supplier ?? "Supplier unknown"}</strong> quoted {dateLabel(o.evidence.arrival_on!)}. {o.level === "watchlist" ? o.applies_because : "Delivery scope matches; technical suitability still needs verification."}</p>)}</div> : null}
    </section>
    <section className="rs-risk-documents"><div className="rs-risk-heading"><h3>Dated source documents</h3><button className="rs-btn rs-btn-sm" disabled={scan.status !== "current"} onClick={() => setAdding(!adding)} aria-expanded={adding}>{adding ? "Cancel" : "Add evidence"}</button></div>
      {adding ? <EvidenceForm part={part} busy={busy} onSave={async (e) => { await onSave(e); setAdding(false); }} /> : null}
      {!part.observations.length ? <p>No supplier quote or delivery evidence has been recorded for this part.</p> : null}
      {[...part.observations].reverse().map((observation) => <EvidencePreview key={observation.evidence.evidence_id} observation={observation} projectId={scan.project_id} />)}
    </section>
    {error ? <p role="alert" className="rs-risk-error">{error}</p> : null}
    <details className="rs-risk-example" open={example} onToggle={(e) => setExample(e.currentTarget.open)}><summary>Preview an illustrative bearing delivery timeline</summary>{example ? <ExampleTimeline /> : null}</details>
    <SourcePreviews scan={scan} />
    <button className="rs-btn rs-btn-sm" onClick={onRefresh} disabled={busy || scan.status !== "current"}>{busy ? "Checking public sources…" : "Refresh public sources"}</button>
    <p className="rs-risk-note">Reassessed when evidence changes. Last web check: {scan.searched_at ? dateLabel(scan.searched_at) : "not yet completed"}.</p>
  </section>;
}

function EvidencePreview({ observation: o, projectId }: { observation: RiskObservation; projectId: string }) {
  const e = o.evidence;
  const url = e.source_url ?? (e.evidence_id.startsWith("import:") && e.source_document_id ? `/api/v1/products/${encodeURIComponent(projectId)}/quotes/${encodeURIComponent(e.source_document_id)}/content` : null);
  return <article className={`rs-risk-document is-${o.level}`}>
    <div className="rs-risk-source-meta"><span><FileText size={14} /> {e.origin === "synthetic_demo" ? "Illustrative sample" : "Provided evidence"}</span><span>{dateLabel(e.issued_on)} · v{e.source_version}</span></div>
    <h4>{url ? <a href={url} target="_blank" rel="noreferrer">{e.title}</a> : e.title}</h4>
    <blockquote>{e.excerpt}</blockquote>
    <p><strong>{o.level === "alert" ? "Why this applies" : o.level === "watchlist" ? "Why this stays on the watchlist" : o.level === "superseded" ? "Earlier estimate" : "Dependency match"}</strong><br />{o.applies_because}</p>
    {e.event ? <small>Changed estimate: {e.event}</small> : null}
  </article>;
}

function ExampleTimeline() {
  const seed = (id: string, issued: string, arrival: string, supplier: string, revision: string | null, event?: string): RiskObservation => ({
    evidence: { evidence_id: id, part_id: "example", kind: "quote", title: `Bearing B-17 · ${supplier}`, excerpt: "Illustrative quote; not a real supplier offer.", issued_on: issued, arrival_on: arrival, supplier, revision, event, source_version: id, origin: "synthetic_demo" },
    level: revision ? arrival > "2026-11-24" ? "alert" : "superseded" : "watchlist", applies_because: revision ? "Illustrative matching revision." : "Revision compatibility still to verify.", days_late: null,
  });
  return <div><p><strong>Illustrative example · not your project data</strong></p><p>Bearing B-17: the revised quote arrives six days late. An earlier alternative still needs revision verification.</p><ArrivalTimeline deadline="2026-11-24" observations={[seed("1", "2026-11-04", "2026-11-22", "Supplier A", "C"), seed("2", "2026-11-10", "2026-11-30", "Supplier A", "C", "Backorder confirmed"), seed("3", "2026-11-12", "2026-11-23", "Supplier B", null)]} /></div>;
}
