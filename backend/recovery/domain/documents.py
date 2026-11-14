"""Applicable documentation planning and autofill (PRD FR-07, FR-13). Pure functions only.

* `plan_package`   — resolves the UK CAA applicability rule for the selected candidate and returns the
                     ordered template list with a plain-language reason for each template.
* `autofill`       — resolves every template `source` expression (grammar in templates/registry) into
                     DraftField dicts with per-field provenance (facts, evidence, checks, transform, origin).
* `validate_draft` — readiness: blocking problems vs explicit completion tasks (signatures/attestations).
* `package_hash`   — stable hash over template ids/versions and field values; review approval binds it.

Values come only from accepted evidence, the accepted decision/selection and case data. Missing
evidence stays visible as a missing field; signatures stay explicit completion tasks for the
responsible person. Nothing here invents a value.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Optional

from .extraction import FIELD_SCHEMAS, coerce, parse_structured_form

# Doc types whose absence means "nothing applicable" rather than missing evidence.
OPTIONAL_DOC_TYPES = {"service_bulletin": "None applicable — no service bulletin in the accepted evidence set"}

ROLE_LABELS = {
    "receiving_inspector": "Operator receiving inspector",
    "quality_manager": "Operator quality manager",
    "supplier_quality_engineer": "Operator supplier quality engineer",
    "manufacturer_certifying_staff": "Manufacturer certifying staff (POA holder)",
    "manufacturer_accountable_manager": "Manufacturer accountable manager",
}

DESTINATION_LABELS = {
    "internal_quality_records": "Operator quality department / technical records system (simulated internal destination)",
    "caa_application_simulated": "UK CAA online application service (simulated — no real application is made)",
    "none": "No destination — package cannot be submitted",
}

TEMPLATE_PURPOSE = {
    "release_certificate": "Authorised release certificate that must accompany the part; the operator verifies and records it.",
    "internal_quality_record": "Internal quality record the operator must complete before the part can be fitted.",
    "authority_application": "Application to the UK CAA required because this route depends on an approval the supplier does not yet hold.",
}

_TOKEN = re.compile(r"\{([^{}]+)\}")


# ----------------------------------------------------------------------------------------------
# Decision helpers
# ----------------------------------------------------------------------------------------------


def candidate_entry(decision: dict, candidate_id: str) -> dict:
    for c in decision.get("candidates", []):
        if c["candidate"]["candidate_id"] == candidate_id:
            return c
    raise KeyError(f"candidate {candidate_id} not in decision {decision.get('decision_id')}")


def candidate_checks(decision: dict, candidate_id: str) -> list[dict]:
    return [c for c in decision.get("checks", []) if c["candidate_id"] == candidate_id]


def _facts_from_catalog(version_ids: list[str], catalog: Any) -> dict[str, dict]:
    """Fallback when a decision payload carries no facts: deterministic structured parse of the evidence."""
    out: dict[str, dict] = {}
    for vid in version_ids:
        ev = catalog.evidence.get(vid)
        if not ev or ev["doc_type"] not in FIELD_SCHEMAS:
            continue
        parsed = parse_structured_form(ev.get("content_text") or "")
        facts = {}
        for fld, typ in FIELD_SCHEMAS[ev["doc_type"]].items():
            if fld not in parsed:
                continue
            raw, line = parsed[fld]
            val, state, note = coerce(typ, raw)
            facts[fld] = {"fact_id": f"fact:{vid}:{fld}", "evidence_version_id": vid, "field": fld, "typed_value": val,
                          "original_value": raw, "locator": {"line": line}, "validation_state": state, "validation_note": note,
                          "extraction_mode": "structured_parse_fallback"}
        out[vid] = facts
    return out


def candidate_facts(decision: dict, candidate_id: str, catalog: Any) -> dict[str, list[tuple[int, str, str, dict]]]:
    """{doc_type: [(authority_rank, effective_at, version_id, fact_map)]} sorted best-first."""
    vids = (decision.get("candidate_evidence") or {}).get(candidate_id)
    if vids is None:
        vids = candidate_entry(decision, candidate_id)["candidate"].get("evidence_ids", [])
    facts = decision.get("facts") or {}
    missing = [v for v in vids if v not in facts]
    if missing:
        facts = {**facts, **_facts_from_catalog(missing, catalog)}
    by_type: dict[str, list[tuple[int, str, str, dict]]] = {}
    for vid in vids:
        ev = catalog.evidence.get(vid)
        if not ev or ev.get("validation_state") == "superseded":
            continue
        by_type.setdefault(ev["doc_type"], []).append((ev.get("authority_rank", 0), ev.get("effective_at") or "", vid, facts.get(vid, {})))
    for lst in by_type.values():
        lst.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return by_type


def best_fact(by_type: dict, doc_type: str, fld: str) -> tuple[Any, Optional[dict], Optional[str]]:
    for _, _, vid, fmap in by_type.get(doc_type, []):
        f = fmap.get(fld)
        if f and f.get("validation_state") == "valid" and f.get("typed_value") not in (None, ""):
            return f["typed_value"], f, vid
    return None, None, None


# ----------------------------------------------------------------------------------------------
# Applicability / package planning
# ----------------------------------------------------------------------------------------------


def applicability_from_decision(decision: dict, candidate_id: str, catalog: Any) -> dict:
    """Same rule semantics as rules.resolve_applicability, computed from the decision's facts."""
    entry = candidate_entry(decision, candidate_id)
    offer = entry["candidate"]
    by_type = candidate_facts(decision, candidate_id, catalog)
    facts: dict[str, Any] = {"route": offer["route"]}
    if offer["route"] == "BUY":
        form, _, _ = best_fact(by_type, "release_certificate", "form_type")
        facts["release_certificate_present"] = form is not None
    else:
        scope, _, _ = best_fact(by_type, "poa_certificate", "scope")
        sites, _, _ = best_fact(by_type, "poa_certificate", "approved_sites")
        comp = catalog.component_for_case(offer["case_id"])
        family = catalog.requirement_sets[comp["requirement_set_id"]]["part_identity"]["family"]
        facts["poa_covers_part_and_site"] = bool(scope and family in scope and offer["site_id"] in (sites or []))
    for rule in catalog.applicability["rules"]:
        if all(facts.get(k) == v for k, v in rule["when"].items()):
            return {"rule": rule, "facts": facts}
    return {"rule": None, "facts": facts}


def plan_package(decision: dict, candidate_id: str, catalog: Any, applicability_ctx: Any = None) -> dict:
    """Returns {rule, facts, templates:[{template, why_included}], destination_type, route_explanation, authority_application}.

    `applicability_ctx` may be a precomputed resolve_applicability() result ({rule, facts}), a
    rules.CandidateContext, or None (derive from the decision payload)."""
    if applicability_ctx is None:
        res = applicability_from_decision(decision, candidate_id, catalog)
    elif isinstance(applicability_ctx, dict) and "rule" in applicability_ctx:
        res = applicability_ctx
    else:
        from .rules import resolve_applicability

        res = resolve_applicability(applicability_ctx)
    rule = res["rule"]
    if rule is None:
        return {"rule": None, "facts": res["facts"], "templates": [], "destination_type": "none",
                "route_explanation": "No applicability rule matched this route; no document package can be generated.", "authority_application": False}
    offer = candidate_entry(decision, candidate_id)["candidate"]
    templates = []
    for tid in rule["package"]:
        tpl = catalog.templates[tid]
        purpose = TEMPLATE_PURPOSE.get(tpl["kind"], "")
        why = (f"{purpose} Required by rule {rule['rule_id']} ({rule['title']}) because this case uses the {offer['route']} route"
               f" with {offer['label'].split(' — ')[0]}. Responsible: {tpl['responsible_applicant']}.")
        templates.append({"template": tpl, "why_included": why})
    return {"rule": rule, "facts": res["facts"], "templates": templates, "destination_type": rule["destination_type"],
            "route_explanation": rule["explanation"].strip(), "authority_application": bool(rule.get("authority_application"))}


def case_info_for(case_id: str, catalog: Any) -> dict:
    comp = catalog.component_for_case(case_id)
    return {
        "case_id": case_id,
        "engine_configuration": f"{catalog.engine['display_name']} — configuration {catalog.engine['configuration_revision']}",
        "position": comp["position"],
        "part_description": f"{comp['display_name']} ({comp['part_identity']} rev {comp['revision']})",
        "display_name": comp["display_name"],
        "component_id": comp["component_id"],
    }


# ----------------------------------------------------------------------------------------------
# Autofill
# ----------------------------------------------------------------------------------------------


class _Resolver:
    def __init__(self, decision: dict, candidate_id: str, case_info: dict, catalog: Any, operator: dict, selection: Optional[dict]):
        self.decision = decision
        self.cid = candidate_id
        self.entry = candidate_entry(decision, candidate_id)
        self.offer = self.entry["candidate"]
        self.case = case_info
        self.catalog = catalog
        self.operator = operator or {}
        self.selection = selection or {}
        self.by_type = candidate_facts(decision, candidate_id, catalog)
        self.checks = candidate_checks(decision, candidate_id)
        self.site = self.entry.get("site") or catalog.sites[self.offer["site_id"]]
        self.supplier = self.entry.get("supplier") or catalog.suppliers[self.offer["supplier_id"]]

    def resolve(self, expr: str) -> tuple[Any, dict]:
        """Returns (value, provenance-dict)."""
        kind, _, arg = expr.partition(":")
        prov: dict[str, Any] = {"source_fact_ids": [], "evidence_refs": [], "check_refs": [], "transform": "copy", "origin": "evidence"}
        if kind == "fact":
            doc_type, _, fld = arg.partition(".")
            val, fact, vid = best_fact(self.by_type, doc_type, fld)
            if fact:
                prov.update(source_fact_ids=[fact["fact_id"]], evidence_refs=[vid])
            elif doc_type in OPTIONAL_DOC_TYPES and not self.by_type.get(doc_type):
                prov.update(origin="computed", transform="optional_absent")
                return OPTIONAL_DOC_TYPES[doc_type], prov
            return val, prov
        if kind == "const":
            prov.update(origin="computed", transform="const")
            return arg, prov
        if kind == "task":
            prov.update(origin="completion_task", transform="task")
            return None, prov
        if kind == "offer":
            prov.update(origin="selection", evidence_refs=[e for e in self.offer.get("evidence_ids", []) if "-q-" in e][:1])
            return self._offer(arg), prov
        if kind == "site":
            prov.update(origin="decision")
            if arg == "otd_label":
                m = next((r for r in self.entry.get("reliability", []) if r["metric_name"] == "on_time_delivery_rate"), None) \
                    or self.catalog.metric(self.site["site_id"], "on_time_delivery_rate")
                if m and m.get("source_evidence_id"):
                    prov["evidence_refs"] = [m["source_evidence_id"]]
                prov["transform"] = "derived:otd_label"
            return self._site(arg), prov
        if kind == "supplier":
            prov.update(origin="decision")
            return self.supplier.get(arg), prov
        if kind == "plan":
            prov.update(origin="computed", transform="plan")
            plan = self.entry.get("plan") or {}
            v = plan.get(arg)
            if isinstance(v, float) and v.is_integer():
                v = int(v)
            return v, prov
        if kind == "case":
            prov.update(origin="case")
            return self.case.get(arg), prov
        if kind == "decision":
            prov.update(origin="decision", transform=f"derived:{arg}")
            return self._decision(arg), prov
        if kind == "selection":
            prov.update(origin="selection")
            return self.selection.get(arg), prov
        if kind == "operator":
            prov.update(origin="case")
            return self.operator.get(arg), prov
        if kind == "check":
            code = arg
            if arg == "REL_OR_POA":
                code = "REL" if self.offer["route"] == "BUY" else "POA"
            chk = next((c for c in self.checks if c.get("template_code") == code), None)
            if chk is None:  # fall back to the requirement ID convention REQ-<SET>-<CODE>-01
                chk = next((c for c in self.checks if c["requirement_id"].split("-")[-2:-1] == [code]), None)
            prov.update(origin="decision", transform="check_summary")
            if not chk:
                return None, prov
            prov.update(check_refs=[chk["check_id"]], evidence_refs=list(chk.get("evidence_refs", [])), source_fact_ids=list(chk.get("fact_refs", [])))
            return f"{chk['result'].upper()} — {chk['explanation']}", prov
        raise ValueError(f"unknown source expression {expr}")

    def _offer(self, attr: str) -> Any:
        o = self.offer
        if attr == "part_revision":
            return f"{o['part_id']} rev {o['revision']}"
        if attr == "route_scope":
            comp = self.catalog.component_for_case(o["case_id"])
            if o["route"] == "BUY":
                roles = ", ".join(self.supplier.get("roles", [])) or "seller"
                return f"Supply of {comp['display_name']} ({o['part_id']}) as {roles} — BUY route, condition {o.get('condition') or 'n/a'}"
            return (f"Manufacture of {comp['display_name']} ({o['part_id']} rev {o['revision']}) at {self.site['name']} under production approval"
                    " — MAKE route")
        if attr == "route":
            return f"{o['route']} — {'buy an existing spare' if o['route'] == 'BUY' else 'commission manufacture'}"
        return o.get(attr)

    def _site(self, attr: str) -> Any:
        s = self.site
        if attr == "supplier_and_site":
            return f"{self.supplier['legal_entity_name']} — {s['name']} ({s['site_id']})"
        if attr == "name_and_address":
            return f"{s['name']}, {s['address']} ({s['site_id']})"
        if attr == "otd_label":
            m = next((r for r in self.entry.get("reliability", []) if r["metric_name"] == "on_time_delivery_rate"), None) \
                or self.catalog.metric(s["site_id"], "on_time_delivery_rate")
            if not m:
                return None
            frac = f" ({int(m['numerator'])}/{int(m['denominator'])})" if m.get("numerator") is not None and m.get("denominator") else ""
            note = "scenario fixture, not measured real-world performance" if m.get("data_origin") == "synthetic_demo" else m.get("data_origin")
            return f"{m['value'] * 100:.1f}% on-time{frac}, {m['window']} — {note}"
        return s.get(attr)

    def _decision(self, attr: str) -> Any:
        d = self.decision
        if attr == "label_and_id":
            return f"{d.get('label', '?')} ({d['decision_id']}), evidence set {d.get('evidence_set_id', '?')}"
        if attr == "exposure_label":
            ex = self.entry.get("exposure") or {}
            if "value" not in ex:
                return None
            sigs = ", ".join(s["title"] for s in ex.get("signals", [])) or "no active disruption signals"
            return f"{ex['value']:.2f} on a 0–1 scale (baseline {ex.get('baseline', 0):.2f}); {sigs}"
        return d.get(attr)


def _apply_transform(transform: str, value: Any, resolver: _Resolver, prov: dict) -> Any:
    def repl(m: re.Match) -> str:
        tok = m.group(1)
        if tok == "value":
            return "" if value is None else str(value)
        v, p = resolver.resolve(tok)
        for k in ("source_fact_ids", "evidence_refs", "check_refs"):
            prov[k] = sorted(set(prov[k]) | set(p.get(k, [])))
        return "" if v is None else str(v)

    return _TOKEN.sub(repl, transform)


def autofill(template: dict, decision: dict, candidate_id: str, case_info: dict, catalog: Any, operator: Optional[dict] = None,
             selection: Optional[dict] = None) -> list[dict]:
    r = _Resolver(decision, candidate_id, case_info, catalog, operator or {}, selection)
    out: list[dict] = []
    for spec in template["fields"]:
        source = spec["source"]
        value, prov = r.resolve(source)
        required = spec.get("required", True)
        editable = spec.get("editable", True)
        status = "filled"
        responsible = None
        note = spec.get("note")
        if source.startswith("task:"):
            role = source.split(":", 1)[1]
            status = "completion_task"
            responsible = ROLE_LABELS.get(role, role.replace("_", " "))
            note = note or f"Signature/attestation by {responsible}; not autofilled."
        elif value is None or value == "":
            status = "missing"
            value = None
            note = note or ("Required value not found in the accepted evidence." if required else "Not present in evidence (optional).")
        elif spec.get("transform"):
            value = _apply_transform(spec["transform"], value, r, prov)
            prov["transform"] = spec["transform"]
        if source.startswith("check:") and value is not None and not str(value).startswith("PASS"):
            status = "invalid"
            note = "Underlying check is not passing for the accepted decision."
        out.append({
            "field_id": spec["field_id"], "label": spec["label"], "block": spec.get("block"), "value": value, "required": required,
            "editable": editable and not source.startswith("const:"), "status": status, "responsible": responsible, "note": note,
            "provenance": {**prov, "edited_by": None, "edited_at": None},
        })
    return out


def validate_draft(fields: list[dict]) -> dict:
    blocking, tasks = [], []
    for f in fields:
        if f["status"] == "completion_task":
            tasks.append({"field_id": f["field_id"], "label": f["label"], "responsible": f.get("responsible")})
        elif f["status"] in ("missing", "invalid") and f.get("required", True):
            blocking.append({"field_id": f["field_id"], "label": f["label"], "status": f["status"], "reason": f.get("note")})
    filled = sum(1 for f in fields if f["status"] == "filled")
    return {"ready": not blocking, "blocking": blocking, "completion_tasks": tasks, "filled": filled, "total": len(fields)}


def merge_readiness(validations: list[dict]) -> dict:
    blocking = [b for v in validations for b in v["blocking"]]
    tasks = [t for v in validations for t in v["completion_tasks"]]
    return {"ready": not blocking, "blocking": blocking, "completion_tasks": tasks,
            "filled": sum(v["filled"] for v in validations), "total": sum(v["total"] for v in validations),
            "note": "Completion tasks (signatures/attestations) remain with the responsible person; they do not block the simulated submission."}


def draft_hash(draft: dict) -> str:
    body = {"template_id": draft["template_id"], "template_version": draft["template_version"],
            "fields": [[f["field_id"], f.get("value")] for f in draft["fields"]]}
    return "sha256:" + hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def package_hash(drafts: list[dict]) -> str:
    body = sorted(([d["template_id"], d["template_version"], [[f["field_id"], f.get("value")] for f in d["fields"]]] for d in drafts),
                  key=lambda x: x[0])
    return "sha256:" + hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def form_template_view(tpl: dict, why: Optional[str] = None) -> dict:
    """Registry entry → FormTemplate contract shape."""
    keys = ["template_id", "title", "owner", "authority", "version", "source_url", "kind", "applicability_rule_id", "responsible_applicant",
            "signatory", "supporting_evidence", "completion_rules", "destination_type", "fields"]
    out = {k: tpl[k] for k in keys}
    out["why_included"] = why
    return out
