"""Deterministic requirement evaluators (PRD FR-02, FR-07, FR-08).

Each evaluator returns pass / fail / unknown with explanation, evidence and fact references, and the
dependency IDs used by impact propagation. Mandatory unknowns keep a candidate pending; preference
scores only apply after eligibility. Agent prose never changes these results.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .extraction import normalise_for_compare


@dataclass
class Outcome:
    result: str  # pass | fail | unknown
    explanation: str
    evidence_refs: list[str] = field(default_factory=list)
    fact_refs: list[str] = field(default_factory=list)
    dependency_ids: list[str] = field(default_factory=list)
    contradictions: list[dict] = field(default_factory=list)
    gap: Optional[dict] = None  # {desired, allowed_sources, priority}
    signal_versions: dict[str, int] = field(default_factory=dict)
    feasible_if_unknown: bool = False  # an unknown that still indicates a feasible (not ready-to-select) plan


@dataclass
class CandidateContext:
    case_id: str
    offer: dict
    site: dict
    supplier: dict
    route: dict
    component: dict
    docs: list[dict]  # active evidence versions for this candidate (incl. follow-ups)
    facts: dict[str, dict[str, dict]]  # version_id -> field -> fact dict
    now: datetime
    signals: list[dict]  # active signals matched to this candidate's route/site/origin
    applicability: dict
    requirement_set: dict

    # ------------------------------------------------------------------
    def docs_of(self, doc_type: str) -> list[dict]:
        return [d for d in self.docs if d["doc_type"] == doc_type]

    def is_expired(self, ev: dict) -> bool:
        exp = ev.get("expiry_at")
        if not exp:
            return False
        exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00")) if isinstance(exp, str) else exp
        return exp_dt < self.now

    def fact(self, doc_type: str, fld: str, *, site_scoped: bool = False) -> tuple[Any, Optional[dict], Optional[dict], list[dict]]:
        """Best valid fact for (doc_type, field) by authority rank then effective date.

        Returns (value, fact, evidence, contradictions). Superseded/expired evidence is ignored for the
        value but contradictions between current sources are preserved."""
        candidates = []
        for ev in self.docs_of(doc_type):
            if ev.get("validation_state") == "superseded":
                continue
            if site_scoped and ev.get("site_id") and ev.get("site_id") != self.offer["site_id"]:
                continue
            f = self.facts.get(ev["version_id"], {}).get(fld)
            if not f or f.get("validation_state") != "valid" or f.get("typed_value") in (None, ""):
                continue
            candidates.append((ev.get("authority_rank", 0), ev.get("effective_at") or "", ev, f))
        if not candidates:
            return None, None, None, []
        candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
        best = candidates[0]
        contradictions = []
        for _, _, ev, f in candidates[1:]:
            if normalise_for_compare(f["typed_value"]) != normalise_for_compare(best[3]["typed_value"]):
                contradictions.append({
                    "field": f"{doc_type}.{fld}", "kept": {"evidence": best[2]["version_id"], "value": best[3]["typed_value"]},
                    "other": {"evidence": ev["version_id"], "value": f["typed_value"]},
                    "resolution": "higher authority rank / newer effective date wins; other value preserved",
                })
        return best[3]["typed_value"], best[3], best[2], contradictions


Evaluator = Callable[[CandidateContext, dict], Outcome]
EVALUATORS: dict[str, Evaluator] = {}


def evaluator(name: str):
    def deco(fn: Evaluator) -> Evaluator:
        EVALUATORS[name] = fn
        return fn
    return deco


def _refs(*items: Optional[dict]) -> tuple[list[str], list[str]]:
    ev, facts = [], []
    for it in items:
        if not it:
            continue
        if "fact_id" in it:
            facts.append(it["fact_id"])
            ev.append(it["evidence_version_id"])
        elif "version_id" in it:
            ev.append(it["version_id"])
    return sorted(set(ev)), sorted(set(facts))


def _current_sb(ctx: CandidateContext) -> tuple[Optional[dict], Optional[dict]]:
    sbs = [d for d in ctx.docs_of("service_bulletin") if d.get("validation_state") != "superseded"]
    if not sbs:
        return None, None
    sbs.sort(key=lambda d: (d.get("revision") or "", d.get("effective_at") or ""), reverse=True)
    sb = sbs[0]
    return sb, ctx.facts.get(sb["version_id"], {})


# ----------------------------------------------------------------------------------------------
@evaluator("part_identity")
def part_identity(ctx: CandidateContext, req: dict) -> Outcome:
    pid = req["params"]["part_identity"]
    required_pn, required_rev = pid["part_number"], pid["revision"]
    pn, pn_f, pn_ev, c1 = ctx.fact("release_certificate", "part_number")
    rev, rev_f, _, c2 = ctx.fact("release_certificate", "revision")
    source = "release certificate"
    if pn is None:
        pn, pn_f, pn_ev, c1 = ctx.fact("quote", "part_number")
        rev, rev_f, _, c2 = ctx.fact("quote", "revision")
        source = "supplier quote"
    q_pn, q_pn_f, _, _ = ctx.fact("quote", "part_number")
    contradictions = c1 + c2
    if pn_f and q_pn_f and normalise_for_compare(pn) != normalise_for_compare(q_pn):
        contradictions.append({"field": "part_number", "kept": {"evidence": pn_f["evidence_version_id"], "value": pn},
                               "other": {"evidence": q_pn_f["evidence_version_id"], "value": q_pn},
                               "resolution": "release certificate (rank 80) outranks supplier quote (rank 40)"})
    allowed, allowed_f, _, _ = ctx.fact("ipc_extract", "interchangeable_revisions")
    allowed = allowed or [required_rev]
    ev_refs, fact_refs = _refs(pn_f, rev_f, allowed_f, q_pn_f)
    deps = [ctx.offer["candidate_id"], ctx.offer["part_id"], *ev_refs]
    if pn is None or rev is None:
        return Outcome("unknown", "No validated part number/revision on a release certificate or quote.", ev_refs, fact_refs, deps,
                       contradictions, gap={"desired": "Release certificate or quote stating part number and revision",
                                            "allowed_sources": ["supplier_replies", "seeded_offers"], "priority": 1})
    base_pn = str(pn).split("-")[0:3]
    if str(pn).upper() != required_pn.upper():
        near = "-".join(base_pn) == required_pn.upper()
        return Outcome("fail", f"{source.capitalize()} shows part {pn}, required {required_pn}" + (" (near-match identifier)." if near else "."),
                       ev_refs, fact_refs, deps, contradictions)
    if str(rev).upper() not in [a.upper() for a in allowed]:
        return Outcome("fail", f"Revision {rev} is not an interchangeable revision for {required_pn} (allowed: {', '.join(allowed)}). Near-match part rejected.",
                       ev_refs, fact_refs, deps, contradictions)
    return Outcome("pass", f"{source.capitalize()} identifies {pn} revision {rev}; allowed revisions {', '.join(allowed)}.",
                   ev_refs, fact_refs, deps, contradictions)


@evaluator("interchangeability")
def interchangeability(ctx: CandidateContext, req: dict) -> Outcome:
    config = "RS-TF2-CFG-A"
    rev = ctx.offer["revision"]
    allowed, a_f, a_ev, _ = ctx.fact("ipc_extract", "interchangeable_revisions")
    excluded, x_f, _, _ = ctx.fact("ipc_extract", "non_interchangeable_revisions")
    eff, e_f, _, _ = ctx.fact("ipc_extract", "effectivity")
    sb, sb_facts = _current_sb(ctx)
    ev_refs, fact_refs = _refs(a_f, x_f, e_f)
    if sb:
        ev_refs = sorted(set(ev_refs + [sb["version_id"]]))
    deps = [ctx.offer["candidate_id"], ctx.offer["part_id"], *ev_refs]
    if allowed is None or eff is None:
        return Outcome("unknown", "No validated illustrated parts catalogue extract for this part.", ev_refs, fact_refs, deps,
                       gap={"desired": "IPC interchangeability/effectivity extract", "allowed_sources": ["evidence_search"], "priority": 1})
    if config not in eff:
        return Outcome("fail", f"IPC effectivity {', '.join(eff)} does not include configuration {config}.", ev_refs, fact_refs, deps)
    if excluded and rev in excluded:
        return Outcome("fail", f"IPC lists revision {rev} as NOT interchangeable on {config}.", ev_refs, fact_refs, deps)
    if rev not in allowed:
        return Outcome("fail", f"Revision {rev} not among interchangeable revisions {', '.join(allowed)}.", ev_refs, fact_refs, deps)
    sb_note = ""
    if sb:
        sbn = (sb_facts.get("sb_number") or {}).get("typed_value", "service bulletin")
        sb_note = f" Current {sbn} Rev {sb.get('revision')} reviewed."
    return Outcome("pass", f"IPC: revision {rev} interchangeable on {config} (allowed {', '.join(allowed)}).{sb_note}", ev_refs, fact_refs, deps)


@evaluator("release_certificate")
def release_certificate(ctx: CandidateContext, req: dict) -> Outcome:
    p = req["params"]
    form, form_f, form_ev, contr = ctx.fact("release_certificate", "form_type")
    deps = [ctx.offer["candidate_id"], ctx.offer["site_id"]]
    if form is None:
        return Outcome("unknown", "No authorised release certificate (CAA Form 1) has been provided for this unit.", [], [], deps,
                       gap={"desired": "CAA Form 1 release certificate for the offered serial number",
                            "allowed_sources": ["supplier_replies"], "priority": 1})
    appr, appr_f, _, _ = ctx.fact("release_certificate", "approval_reference")
    pn, pn_f, _, _ = ctx.fact("release_certificate", "part_number")
    sn, sn_f, _, _ = ctx.fact("release_certificate", "serial_number")
    status, st_f, _, _ = ctx.fact("release_certificate", "status_work")
    ev_refs, fact_refs = _refs(form_f, appr_f, pn_f, sn_f, st_f)
    deps += ev_refs
    if form not in p["accepted_forms"]:
        return Outcome("fail", f"Certificate type '{form}' is not an accepted release certificate.", ev_refs, fact_refs, deps, contr)
    if not appr:
        return Outcome("unknown", "Release certificate lacks an approval reference.", ev_refs, fact_refs, deps, contr,
                       gap={"desired": "Approval reference of issuing organisation", "allowed_sources": ["supplier_replies"], "priority": 2})
    if status not in p["accepted_status"]:
        return Outcome("fail", f"Block 11 status '{status}' is not acceptable for installation.", ev_refs, fact_refs, deps, contr)
    return Outcome("pass", f"{form} {appr} releases S/N {sn} as {status}.", ev_refs, fact_refs, deps, contr)


@evaluator("traceability")
def traceability(ctx: CandidateContext, req: dict) -> Outcome:
    b2b, b_f, b_ev, _ = ctx.fact("trace_pack", "back_to_birth")
    nis, n_f, _, _ = ctx.fact("trace_pack", "non_incident_statement")
    sn, sn_f, _, _ = ctx.fact("trace_pack", "serial_number")
    cert_sn, c_f, _, _ = ctx.fact("release_certificate", "serial_number")
    ev_refs, fact_refs = _refs(b_f, n_f, sn_f, c_f)
    deps = [ctx.offer["candidate_id"], *ev_refs]
    gap = {"desired": "Back-to-birth trace pack with non-incident statement", "allowed_sources": ["supplier_replies"], "priority": 1}
    if b2b is None or nis is None:
        return Outcome("unknown", "Traceability pack missing or incomplete (back-to-birth / non-incident statement not evidenced).",
                       ev_refs, fact_refs, deps, gap=gap)
    if cert_sn and sn and cert_sn != sn:
        return Outcome("fail", f"Trace pack serial {sn} does not match release certificate serial {cert_sn}.", ev_refs, fact_refs, deps)
    if not b2b or not nis:
        return Outcome("fail", "Supplier cannot confirm back-to-birth traceability and a non-incident statement.", ev_refs, fact_refs, deps)
    return Outcome("pass", f"Back-to-birth trace and non-incident statement confirmed for S/N {sn}.", ev_refs, fact_refs, deps)


@evaluator("quality_certificate_site")
def quality_certificate_site(ctx: CandidateContext, req: dict) -> Outcome:
    route = ctx.offer["route"]
    standards = req["params"]["standards"][route]
    site_id = ctx.offer["site_id"]
    deps = [ctx.offer["candidate_id"], site_id, ctx.offer["supplier_id"]]
    certs = ctx.docs_of("quality_certificate")
    own, other_site = [], []
    for ev in certs:
        facts = ctx.facts.get(ev["version_id"], {})
        cs = (facts.get("certified_site") or {}).get("typed_value")
        (own if cs == site_id else other_site).append((ev, facts))
    ev_refs = sorted({ev["version_id"] for ev, _ in own + other_site})
    deps += ev_refs
    fact_refs = sorted({f["fact_id"] for _, facts in own for f in facts.values()})
    if not own:
        if other_site:
            names = ", ".join((f.get("certified_site") or {}).get("typed_value", "?") for _, f in other_site)
            return Outcome("unknown", f"Only certificates for other sites ({names}) were found; they do not qualify {site_id}.",
                           ev_refs, fact_refs, deps,
                           gap={"desired": f"Quality certificate naming site {site_id}", "allowed_sources": ["supplier_replies"], "priority": 2},
                           feasible_if_unknown=True)
        return Outcome("unknown", f"No quality system certificate found for {site_id}.", ev_refs, fact_refs, deps,
                       gap={"desired": f"{' or '.join(standards)} certificate for {site_id}", "allowed_sources": ["supplier_replies"], "priority": 2})
    ev, facts = own[0]
    std = (facts.get("standard") or {}).get("typed_value")
    num = (facts.get("certificate_number") or {}).get("typed_value")
    exp = (facts.get("expiry_date") or {}).get("typed_value")
    if std not in standards:
        return Outcome("fail", f"Certificate standard {std} not accepted for {route} (needs {', '.join(standards)}).", ev_refs, fact_refs, deps)
    if ctx.is_expired(ev):
        return Outcome("fail", f"{std} certificate {num} for {site_id} expired on {exp}.", ev_refs, fact_refs, deps)
    return Outcome("pass", f"{std} certificate {num} covers {ctx.site['name']} until {exp}.", ev_refs, fact_refs, deps)


@evaluator("legal_entity")
def legal_entity(ctx: CandidateContext, req: dict) -> Outcome:
    status, s_f, s_ev, _ = ctx.fact("registry_extract", "status")
    name, n_f, _, _ = ctx.fact("registry_extract", "legal_entity_name")
    ev_refs, fact_refs = _refs(s_f, n_f)
    deps = [ctx.offer["supplier_id"], *ev_refs]
    if status is None:
        return Outcome("unknown", "No company registry evidence for the selling entity.", ev_refs, fact_refs, deps,
                       gap={"desired": "Company registry extract", "allowed_sources": ["companies_house", "evidence_search"], "priority": 3})
    if name and name != ctx.supplier["legal_entity_name"]:
        return Outcome("fail", f"Registry entity '{name}' differs from contracting entity '{ctx.supplier['legal_entity_name']}'.", ev_refs, fact_refs, deps)
    if str(status).lower() != "active":
        return Outcome("fail", f"Registry status is '{status}'.", ev_refs, fact_refs, deps)
    origin = " (synthetic registry extract)" if s_ev and s_ev.get("data_origin") == "synthetic_demo" else ""
    return Outcome("pass", f"{name} is an active registered entity{origin}.", ev_refs, fact_refs, deps)


@evaluator("quote_valid")
def quote_valid(ctx: CandidateContext, req: dict) -> Outcome:
    valid_until, v_f, q_ev, _ = ctx.fact("quote", "quote_valid_until")
    qty, q_f, _, _ = ctx.fact("quote", "quantity")
    price, p_f, _, _ = ctx.fact("quote", "unit_price")
    ev_refs, fact_refs = _refs(v_f, q_f, p_f)
    deps = [ctx.offer["candidate_id"], *ev_refs]
    if valid_until is None or qty is None or price is None:
        return Outcome("unknown", "Quotation incomplete (validity, quantity or price not evidenced).", ev_refs, fact_refs, deps,
                       gap={"desired": "Complete quotation", "allowed_sources": ["supplier_replies"], "priority": 2})
    if datetime.fromisoformat(valid_until).replace(tzinfo=timezone.utc).date() < ctx.now.date():
        return Outcome("fail", f"Quote expired on {valid_until}.", ev_refs, fact_refs, deps)
    if int(qty) < ctx.offer.get("quantity", 1):
        return Outcome("fail", f"Quote covers {qty} unit(s), {ctx.offer.get('quantity', 1)} required.", ev_refs, fact_refs, deps)
    return Outcome("pass", f"Quote valid until {valid_until} for {qty} unit(s).", ev_refs, fact_refs, deps)


@evaluator("production_approval")
def production_approval(ctx: CandidateContext, req: dict) -> Outcome:
    family = req["params"]["family"]
    site_id = ctx.offer["site_id"]
    scope, s_f, s_ev, _ = ctx.fact("poa_certificate", "scope")
    sites, st_f, _, _ = ctx.fact("poa_certificate", "approved_sites")
    ref, r_f, _, _ = ctx.fact("poa_certificate", "approval_reference")
    ev_refs, fact_refs = _refs(s_f, st_f, r_f)
    deps = [ctx.offer["candidate_id"], site_id, ctx.offer["supplier_id"], *ev_refs]
    if scope is None:
        return Outcome("unknown", "No production organisation approval evidence for the manufacturer.", ev_refs, fact_refs, deps,
                       gap={"desired": "UK Part 21G approval certificate and scope", "allowed_sources": ["supplier_replies"], "priority": 1})
    if family not in scope:
        return Outcome("fail", f"POA {ref} scope ({', '.join(scope)}) does not cover {family}.", ev_refs, fact_refs, deps)
    if site_id not in (sites or []):
        return Outcome("unknown", f"POA {ref} approves sites {', '.join(sites or [])}; {site_id} is not an approved production site "
                       "(site-specific approval cannot be assumed). A Part 21 Subpart F agreement would be required.",
                       ev_refs, fact_refs, deps,
                       gap={"desired": f"POA scope extension to {site_id} or CAA Form 65 letter of agreement", "allowed_sources": ["supplier_replies"], "priority": 1},
                       feasible_if_unknown=True)
    return Outcome("pass", f"POA {ref} covers {family} at {ctx.site['name']}.", ev_refs, fact_refs, deps)


def _rev_ge(a: str, b: str) -> bool:
    return (a or "").upper() >= (b or "").upper()


@evaluator("design_data")
def design_data(ctx: CandidateContext, req: dict) -> Outcome:
    drev, d_f, d_ev, _ = ctx.fact("design_licence", "drawing_revision")
    licensee, l_f, _, _ = ctx.fact("design_licence", "licensee")
    sb, sb_facts = _current_sb(ctx)
    ev_refs, fact_refs = _refs(d_f, l_f)
    min_rev = None
    if sb:
        ev_refs = sorted(set(ev_refs + [sb["version_id"]]))
        mf = sb_facts.get("min_drawing_revision")
        if mf and mf.get("validation_state") == "valid":
            min_rev = mf["typed_value"]
            fact_refs = sorted(set(fact_refs + [mf["fact_id"]]))
    deps = [ctx.offer["candidate_id"], ctx.offer["part_id"], *ev_refs]
    if drev is None:
        return Outcome("unknown", "No design data licence evidenced for the manufacturer.", ev_refs, fact_refs, deps,
                       gap={"desired": "Design data licence from the design holder", "allowed_sources": ["supplier_replies"], "priority": 1})
    if licensee and licensee != ctx.supplier["legal_entity_name"]:
        return Outcome("fail", f"Licence is held by {licensee}, not the manufacturer.", ev_refs, fact_refs, deps)
    if min_rev and not _rev_ge(drev, min_rev):
        return Outcome("fail", f"Licensed drawing revision {drev} is below the minimum revision {min_rev} required by the current service bulletin "
                       f"(Rev {sb.get('revision')}).", ev_refs, fact_refs, deps)
    tail = f" ≥ minimum {min_rev} per current SB Rev {sb.get('revision')}" if min_rev else ""
    return Outcome("pass", f"Licensed to build to drawing revision {drev}{tail}.", ev_refs, fact_refs, deps)


@evaluator("special_process")
def special_process(ctx: CandidateContext, req: dict) -> Outcome:
    needed = ctx.offer.get("route_specific", {}).get("special_processes", [])
    site_id = ctx.offer["site_id"]
    deps = [ctx.offer["candidate_id"], site_id]
    best = None
    for ev in ctx.docs_of("special_process_accreditation"):
        facts = ctx.facts.get(ev["version_id"], {})
        if (facts.get("site") or {}).get("typed_value") != site_id:
            continue
        if best is None or ev["authority_rank"] > best[0]["authority_rank"]:
            best = (ev, facts)
    if best is None:
        return Outcome("unknown", f"No special-process accreditation evidence for {site_id}.", [], [], deps,
                       gap={"desired": f"Nadcap accreditation for {site_id}", "allowed_sources": ["supplier_replies"], "priority": 2})
    ev, facts = best
    have = (facts.get("processes") or {}).get("typed_value") or []
    ev_refs = [ev["version_id"]]
    fact_refs = sorted(f["fact_id"] for f in facts.values())
    deps += ev_refs
    missing = [p for p in needed if p not in have]
    weak = ev["authority_rank"] < 70
    if ctx.is_expired(ev):
        return Outcome("fail", f"Process accreditation for {site_id} has expired.", ev_refs, fact_refs, deps)
    if missing:
        return Outcome("unknown" if weak else "fail",
                       f"Site evidence covers {', '.join(have) or 'no processes'}; missing {', '.join(missing)}"
                       + (" (supplier statement only, accreditation not evidenced)." if weak else "."),
                       ev_refs, fact_refs, deps,
                       gap={"desired": f"Accreditation for {', '.join(missing)} at {site_id}", "allowed_sources": ["supplier_replies"], "priority": 2} if weak else None)
    if weak:
        return Outcome("unknown", f"Supplier states capability for {', '.join(needed)} at {site_id}, but no accreditation record is evidenced. "
                       "Capability looks feasible; not ready to select.", ev_refs, fact_refs, deps,
                       gap={"desired": f"Nadcap accreditation record for {site_id}", "allowed_sources": ["supplier_replies"], "priority": 2},
                       feasible_if_unknown=True)
    return Outcome("pass", f"Accredited at {ctx.site['name']} for {', '.join(needed)}.", ev_refs, fact_refs, deps)


@evaluator("first_article")
def first_article(ctx: CandidateContext, req: dict) -> Outcome:
    result, r_f, r_ev, _ = ctx.fact("fai_report", "result")
    site, s_f, _, _ = ctx.fact("fai_report", "site")
    rep, n_f, _, _ = ctx.fact("fai_report", "report_number")
    ev_refs, fact_refs = _refs(r_f, s_f, n_f)
    deps = [ctx.offer["candidate_id"], ctx.offer["site_id"], *ev_refs]
    gap = {"desired": "AS9102 first article inspection report for this part at this site", "allowed_sources": ["supplier_replies"], "priority": 3}
    if result is None:
        return Outcome("unknown", "No first article inspection yet: plan is feasible but not ready to select.", ev_refs, fact_refs, deps, gap=gap,
                       feasible_if_unknown=True)
    if site != ctx.offer["site_id"]:
        return Outcome("unknown", f"FAI {rep} was performed at {site}, not {ctx.offer['site_id']}.", ev_refs, fact_refs, deps, gap=gap,
                       feasible_if_unknown=True)
    if str(result).lower() != "complete":
        return Outcome("unknown", f"FAI {rep} status '{result}'.", ev_refs, fact_refs, deps, gap=gap, feasible_if_unknown=True)
    return Outcome("pass", f"AS9102 FAI {rep} complete at {ctx.site['name']}.", ev_refs, fact_refs, deps)


@evaluator("route_viable")
def route_viable(ctx: CandidateContext, req: dict) -> Outcome:
    route = ctx.route
    deps = [ctx.offer["candidate_id"], route["route_id"], *route.get("passes_through", [])]
    sig_versions = {s["source_event_id"]: s["version"] for s in ctx.signals}
    if not ctx.signals:
        return Outcome("pass", f"No active disruption on {route['label']}.", [], [], deps, signal_versions=sig_versions)
    blocked = [s for s in ctx.signals if s["assertion"].get("type") == "route_blocked"]
    if blocked:
        return Outcome("fail", f"Route blocked by {blocked[0]['title']} with no alternative.", [], [], deps + [s["signal_id"] for s in blocked],
                       signal_versions=sig_versions)
    delays = ", ".join(f"{s['title']} (+{s['assertion'].get('transport_delay_days', 0):g} d)" for s in ctx.signals)
    return Outcome("pass", f"Route open with disruption: {delays}. Reflected in the recovery plan and exposure.", [], [],
                   deps + [s["signal_id"] for s in ctx.signals], signal_versions=sig_versions)


def resolve_applicability(ctx: CandidateContext) -> dict:
    route = ctx.offer["route"]
    facts: dict[str, Any] = {"route": route}
    if route == "BUY":
        form, _, _, _ = ctx.fact("release_certificate", "form_type")
        facts["release_certificate_present"] = form is not None
    else:
        scope, _, _, _ = ctx.fact("poa_certificate", "scope")
        sites, _, _, _ = ctx.fact("poa_certificate", "approved_sites")
        family = ctx.requirement_set["part_identity"]["family"]
        facts["poa_covers_part_and_site"] = bool(scope and family in scope and ctx.offer["site_id"] in (sites or []))
    for rule in ctx.applicability["rules"]:
        if all(facts.get(k) == v for k, v in rule["when"].items()):
            return {"rule": rule, "facts": facts}
    return {"rule": None, "facts": facts}


@evaluator("regulatory_route")
def regulatory_route(ctx: CandidateContext, req: dict) -> Outcome:
    res = resolve_applicability(ctx)
    rule = res["rule"]
    deps = [ctx.offer["candidate_id"], ctx.offer["site_id"]]
    ev_refs = sorted({d["version_id"] for d in ctx.docs if d["doc_type"] in {"release_certificate", "poa_certificate"}})
    if rule is None:
        return Outcome("unknown", "No applicability rule matched this route.", ev_refs, [], deps,
                       gap={"desired": "Applicability determination", "allowed_sources": ["applicability_catalogue"], "priority": 1})
    if rule.get("blocks_selection"):
        return Outcome("unknown", f"{rule['title']}: {rule['explanation']}", ev_refs, [], deps + [rule["rule_id"]],
                       gap={"desired": "Missing approval/certificate required by the applicable route", "allowed_sources": ["supplier_replies"], "priority": 2},
                       feasible_if_unknown=bool(rule.get("authority_application")))
    pkg = ", ".join(rule["package"])
    return Outcome("pass", f"{rule['title']} → package {pkg}; destination {rule['destination_type']}"
                   + ("" if rule.get("authority_application") else " (no authority application needed)."),
                   ev_refs, [], deps + [rule["rule_id"]])


# ----------------------------------------------------------------------------------------------
def check_fingerprint(req: dict, outcome: Outcome) -> str:
    payload = {
        "req": req["requirement_id"], "v": req["version"], "evaluator": f"{req['evaluator_id']}@{req['evaluator_version']}",
        "evidence": sorted(outcome.evidence_refs), "facts": sorted(outcome.fact_refs), "signals": outcome.signal_versions,
        "result": outcome.result, "explanation": outcome.explanation,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:24]


def evaluate(ctx: CandidateContext, req: dict) -> Outcome:
    fn = EVALUATORS[req["evaluator_id"]]
    out = fn(ctx, req)
    out.dependency_ids = sorted(set(out.dependency_ids))
    return out


def eligibility_from(checks: list[dict]) -> tuple[str, bool]:
    """Deterministic mandatory gates. Returns (eligibility, feasible)."""
    mandatory = [c for c in checks if c["mandatory"]]
    if any(c["result"] == "fail" for c in mandatory):
        return "ineligible", False
    unknown = [c for c in mandatory if c["result"] == "unknown"]
    if unknown:
        feasible = all(c.get("feasible_if_unknown") for c in unknown)
        return "pending", feasible
    return "eligible", True
