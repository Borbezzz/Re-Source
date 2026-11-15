import { useState } from "react";
import { motion } from "motion/react";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import type { PackageComponent } from "../data/package.ts";
import { fmtDay, money, type Assessed, type SourcingNeed } from "../data/checks.ts";
import { DESTINATION } from "../data/sites.ts";
import type { ProductProject } from "../../product-flow/types.ts";
import { ComponentThumb } from "../scene/ComponentThumb.tsx";

export type ProcurementStep = "prepared" | "approved" | "sent" | "acknowledged" | "confirmed";
const ORDER: ProcurementStep[] = ["prepared", "approved", "sent", "acknowledged", "confirmed"];

export function Fulfilment({
  glbUrl,
  component,
  need,
  project,
  chosen,
  step,
  busy,
  onApprove,
  onSend,
  onBack,
  onFinish,
  done,
}: {
  glbUrl: string;
  component: PackageComponent;
  need: SourcingNeed;
  project: ProductProject;
  chosen: Assessed | null;
  step: ProcurementStep;
  busy: string | null;
  onApprove: () => void;
  onSend: () => void;
  onBack: () => void;
  onFinish: () => void;
  done: boolean;
}) {
  const pkg = project.package!;
  const item = pkg.items[0];
  const enquiry = pkg.enquiry;
  const [identityOk, setIdentityOk] = useState(false);
  const idx = ORDER.indexOf(step);
  const supplier = chosen ? chosen.candidate.supplier_name.replace(" (sample)", "") : item.supplier_name;
  const quote = project.mailbox?.find((m) => m.direction === "inbound" && m.quote)?.quote;
  const stages: { id: ProcurementStep; title: string; text: string; sim?: boolean }[] = [
    { id: "prepared", title: "Enquiry prepared", text: `RFQ drafted from the reviewed requirements · package ${pkg.package_id.slice(-6)}` },
    { id: "approved", title: "Approved for sending", text: "Buyer approval recorded. Unverified supplier evidence acknowledged." },
    { id: "sent", title: "Sent to supplier", text: pkg.receipt ? `Receipt ${pkg.receipt}` : "Enquiry and document requests delivered to the supplier." },
    { id: "acknowledged", title: "Acknowledged", text: `${supplier} acknowledged the enquiry and document requests.`, sim: true },
    {
      id: "confirmed",
      title: "Quote confirmed",
      text: `${money(quote?.price ?? chosen?.candidate.price, "GBP")} · dispatch ${quote?.lead_time_days ?? chosen?.dispatchDays ?? "?"} days. Order not yet committed.`,
      sim: true,
    },
  ];
  return (
    <motion.div className="rs-fulfil" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6 }}>
      <div className="rs-fulfil-main">
        <section className="rs-anchor rs-panel" style={{ position: "absolute", top: 18, left: 24 }}>
          <div className="rs-anchor-head" style={{ cursor: "default" }}>
            <ComponentThumb url={glbUrl} nodeIds={component.nodeIds} label={component.name} />
            <span>
              <span className="rs-anchor-title" style={{ display: "block" }}>{component.name}</span>
              <span className="rs-anchor-sub rs-mono" style={{ display: "block" }}>{component.partNumber} · Rev {component.revision}</span>
            </span>
            <span />
          </div>
        </section>
        <div style={{ display: "grid", gap: 8, maxWidth: 760 }}>
          <span className="rs-eyebrow">Prepare fulfilment</span>
          <h1 className="rs-h1" style={{ fontSize: 40 }}>
            Review the enquiry to <span className="rs-grad-text">{supplier}</span>
          </h1>
          <p className="rs-lede" style={{ fontSize: 16 }}>
            {chosen ? `${chosen.site.siteType}, ${chosen.site.city}` : ""} · Requested on site by {fmtDay(need.requiredBy)} at {DESTINATION.name}
          </p>
        </div>
        <article className="rs-doc" style={{ maxWidth: 760 }} aria-label="Request for quotation">
          <div className="rs-doc-head">
            <span>Email draft · {pkg.status === "draft" ? "Ready for review" : pkg.status === "approved" ? "Approved" : "Sent"}</span>
            <span>{new Date(pkg.created_at).toLocaleDateString("en-GB")}</span>
          </div>
          <dl className="rs-email-envelope">
            <dt>To</dt><dd>{supplier} sales team</dd>
            <dt>From</dt><dd>{enquiry?.buyer_contact ?? "Procurement desk"} · {enquiry?.buyer_company ?? "Aldbury Aero Maintenance Ltd"}</dd>
            <dt>Subject</dt><dd>{item.rfq_subject || `Request for quotation — ${component.partNumber} — Qty ${item.quantity}`}</dd>
          </dl>
          <div className="rs-email-body">{item.rfq_text}</div>
        </article>
        <div style={{ display: "flex", gap: 10, maxWidth: 760 }}>
          <button type="button" className="rs-btn rs-btn-ghost" onClick={onBack} disabled={idx > 0}>
            <ArrowLeft size={15} /> Back to shortlist
          </button>
        </div>
      </div>
      <aside className="rs-fulfil-side" aria-label="Procurement status">
        <section style={{ display: "grid", gap: 12 }}>
          <h2 className="rs-h3">Buyer identity</h2>
          <dl className="rs-kv">
            <dt>Company</dt>
            <dd>{enquiry?.buyer_company ?? "Aldbury Aero Maintenance Ltd"}</dd>
            <dt>Contact</dt>
            <dd>{enquiry?.buyer_contact ?? "Procurement desk"}</dd>
            <dt>Site</dt>
            <dd>{DESTINATION.name}</dd>
          </dl>
          <label style={{ display: "flex", gap: 10, alignItems: "flex-start", fontSize: 13.5, color: "var(--rs-text-2)" }}>
            <input type="checkbox" checked={identityOk || idx > 0} disabled={idx > 0} onChange={(e) => setIdentityOk(e.target.checked)} style={{ marginTop: 3, accentColor: "#8b5cf6" }} />
            I confirm our company identity and contact details for supplier outreach.
          </label>
        </section>
        <hr className="rs-divider" />
        <ol className="rs-timeline" aria-label="Procurement states">
          {stages.map((s, i) => (
            <li key={s.id} className={`rs-tl${i <= idx ? " is-done" : ""}${i === idx + 1 ? " is-current" : ""}`}>
              <span className="rs-tl-dot">{i <= idx ? <Check size={14} strokeWidth={3} /> : i + 1}</span>
              <div>
                <b>{s.title}</b>
                <p>{s.text}</p>
              </div>
            </li>
          ))}
        </ol>
        {idx === 0 ? (
          <button type="button" className="rs-btn rs-btn-grad" disabled={!identityOk || busy === "approve"} onClick={onApprove}>
            {busy === "approve" ? "Approving…" : "Approve enquiry"}
          </button>
        ) : idx === 1 ? (
          <button type="button" className="rs-btn rs-btn-grad" disabled={busy === "send"} onClick={onSend}>
            {busy === "send" ? "Sending…" : "Send enquiry"}
          </button>
        ) : null}
        <hr className="rs-divider" />
        <section style={{ display: "grid", gap: 10 }}>
          <h2 className="rs-h3">Documents requested from supplier</h2>
          {["Certificate of conformity / authorised release certificate", "Traceability: manufacturer, origin, serial or lot", "Applicability to this assembly configuration"].map((d) => (
            <div key={d} className="rs-small" style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
              <span>{d}</span>
              <span className="rs-badge wait">{idx >= 2 ? "Requested" : "To request"}</span>
            </div>
          ))}
          <p className="rs-tiny" style={{ margin: 0 }}>Certificates are issued by the supplier; Re::Source never generates them. Approval forms are determined per transaction.</p>
        </section>
        <section style={{ display: "grid", gap: 8 }}>
          <h2 className="rs-h3">Delivery</h2>
          <div className="rs-small" style={{ display: "flex", justifyContent: "space-between" }}>
            <span>Plan prepared · {chosen?.site.city ?? ""} → Bristol</span>
            <span className="rs-badge">{idx >= 4 ? "Plan prepared" : "Draft"}</span>
          </div>
          <div className="rs-small" style={{ display: "flex", justifyContent: "space-between" }}>
            <span>Dispatch confirmed</span>
            <span className="rs-badge">Not yet</span>
          </div>
        </section>
        {done ? (
          <button type="button" className="rs-btn rs-btn-grad" onClick={onFinish}>
            Preview reassembly <ArrowRight size={16} />
          </button>
        ) : null}
      </aside>
    </motion.div>
  );
}
