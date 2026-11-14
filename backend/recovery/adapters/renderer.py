"""DocumentRenderer (PRD §5.4, FR-13): reviewable standalone HTML for a document package and its
simulated receipt. Every value is escaped; the page is clearly marked SIMULATED and synthetic."""

from __future__ import annotations

from html import escape
from typing import Any, Optional

_CSS = """
:root{--ink:#14202b;--muted:#5b6b78;--line:#d5dde3;--accent:#0b5cad;--warn:#a15c00;--bad:#b3261e;--ok:#1b6e3a;--paper:#fff;--bg:#f3f5f7}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1080px;margin:0 auto;padding:24px 16px 64px;position:relative}
.watermark{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;pointer-events:none;font-size:110px;font-weight:800;
color:rgba(179,38,30,.07);transform:rotate(-24deg);letter-spacing:.1em}
header h1{margin:0 0 4px;font-size:22px}.meta{color:var(--muted);font-size:13px}
.banner{border:1px solid var(--warn);background:#fff6e8;color:#5a3a00;padding:10px 12px;border-radius:6px;margin:16px 0}
section.doc{background:var(--paper);border:1px solid var(--line);border-radius:8px;margin:18px 0;padding:16px}
section.doc h2{margin:0 0 4px;font-size:17px}.why{color:var(--muted);margin:4px 0 10px}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{border-top:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{background:#f7f9fa;font-weight:600}td.block{width:56px;color:var(--muted)}td.prov{color:var(--muted);font-size:12px;width:30%}
.st{display:inline-block;padding:1px 6px;border-radius:10px;font-size:11px;border:1px solid}
.st.filled{color:var(--ok);border-color:var(--ok)}.st.missing,.st.invalid{color:var(--bad);border-color:var(--bad)}
.st.completion_task{color:var(--warn);border-color:var(--warn)}
.receipt{border:2px dashed var(--accent);border-radius:8px;padding:14px;background:#eef5fc}
code{font-size:12px;word-break:break-all}ul{margin:6px 0 0 18px;padding:0}
@media (max-width:640px){td.prov{display:none}th.prov{display:none}}
"""


def _prov_text(p: dict) -> str:
    parts = [f"origin: {p.get('origin')}"]
    if p.get("transform") and p.get("transform") != "copy":
        parts.append(f"transform: {p['transform']}")
    if p.get("source_fact_ids"):
        parts.append("facts: " + ", ".join(p["source_fact_ids"]))
    if p.get("evidence_refs"):
        parts.append("evidence: " + ", ".join(p["evidence_refs"]))
    if p.get("check_refs"):
        parts.append("checks: " + ", ".join(p["check_refs"]))
    if p.get("edited_by"):
        parts.append(f"edited by {p['edited_by']} at {p.get('edited_at')}")
    return escape(" · ".join(parts))


def render_package(package: dict, drafts: list[dict], templates: dict[str, dict], receipt: Optional[dict] = None,
                   case_title: str = "") -> str:
    docs_html = []
    for d in drafts:
        tpl = templates.get(d["template_id"], {})
        rows = []
        for f in d["fields"]:
            val = "—" if f.get("value") in (None, "") else escape(str(f["value"]))
            resp = f" <em>({escape(f['responsible'])})</em>" if f.get("responsible") else ""
            rows.append(
                f"<tr><td class='block'>{escape(str(f.get('block') or ''))}</td><td>{escape(f['label'])}</td><td>{val}{resp}</td>"
                f"<td><span class='st {escape(f['status'])}'>{escape(f['status'].replace('_', ' '))}</span></td>"
                f"<td class='prov'>{_prov_text(f.get('provenance') or {})}</td></tr>")
        src = tpl.get("source_url", "")
        docs_html.append(
            f"<section class='doc'><h2>{escape(d['template_title'])}</h2>"
            f"<div class='meta'>Template {escape(d['template_id'])} · version {escape(d['template_version'])} · draft v{d['version']} · "
            f"review: {escape(d['review_state'])} · status: {escape(d['status'])}</div>"
            f"<div class='meta'>Source: <a href='{escape(src)}'>{escape(src)}</a> · Owner: {escape(tpl.get('owner', ''))}</div>"
            f"<p class='why'>{escape(d.get('why_included', ''))}</p>"
            f"<table><thead><tr><th>Block</th><th>Field</th><th>Value</th><th>Status</th><th class='prov'>Provenance</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></section>")
    readiness = package.get("readiness") or {}
    tasks = "".join(f"<li>{escape(t['label'])} — {escape(t.get('responsible') or '')}</li>" for t in readiness.get("completion_tasks", []))
    blocking = "".join(f"<li>{escape(b['label'])}: {escape(b.get('reason') or b['status'])}</li>" for b in readiness.get("blocking", []))
    receipt_html = ""
    if receipt:
        docs = "".join(f"<li>{escape(x['title'])} ({escape(x['template_id'])} v{escape(str(x.get('version')))}) — <code>{escape(x['hash'])}</code></li>"
                       for x in receipt.get("submitted_documents", []))
        receipt_html = (
            f"<section class='receipt'><h2>{escape(receipt['label'])}</h2>"
            f"<div>Receipt <code>{escape(receipt['receipt_id'])}</code> · {escape(receipt['simulated_at'])}</div>"
            f"<div>Destination: {escape(receipt['destination_label'])} (<code>{escape(receipt['destination_type'])}</code>)</div>"
            f"<div>Payload hash <code>{escape(receipt['payload_hash'])}</code> · package v{receipt['package_version']} "
            f"<code>{escape(receipt['package_hash'])}</code></div><ul>{docs}</ul></section>")
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>Document package v{package['version']}</title><style>{_CSS}</style></head><body><div class='watermark'>SIMULATED</div><main>"
        f"<header><h1>Document package v{package['version']}{(' — ' + escape(case_title)) if case_title else ''}</h1>"
        f"<div class='meta'>Package <code>{escape(package['package_id'])}</code> · hash <code>{escape(package['package_hash'])}</code> · "
        f"review {escape(package['review_state'])} · status {escape(package['status'])}</div>"
        f"<div class='meta'>Decision {escape(package['decision_id'])} · selection {escape(package['selection_id'])} · evidence set "
        f"{escape(package['evidence_set_id'])} · destination {escape(package['destination_type'])}</div></header>"
        "<div class='banner'>Synthetic demonstration data. Supplier names, part numbers, approval references and documents are fictional. "
        "Regulatory templates are faithful field representations linked to official UK CAA sources. Any submission is SIMULATED.</div>"
        f"<p>{escape(package.get('route_explanation', ''))}</p>"
        + (f"<h3>Blocking items</h3><ul>{blocking}</ul>" if blocking else "")
        + (f"<h3>Completion tasks for responsible people</h3><ul>{tasks}</ul>" if tasks else "")
        + "".join(docs_html) + receipt_html + "</main></body></html>")


def render_receipt_text(receipt: dict[str, Any]) -> str:
    return (f"{receipt['label']}\nReceipt: {receipt['receipt_id']}\nSimulated at: {receipt['simulated_at']}\n"
            f"Destination: {receipt['destination_label']} ({receipt['destination_type']})\nPayload hash: {receipt['payload_hash']}\n")
