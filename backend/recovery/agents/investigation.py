"""Investigation / reassessment graph nodes (PRD §8.1).

load_case → snapshot_requirements → parallel(source_buy, source_make) → normalize_offers →
parallel(extract_and_validate → [supplier_site_checks, technical_checks, regulatory_route]) →
resolve_gaps_if_budget → evaluate_eligibility → schedule_and_rank → persist_decision.

Workers return typed patches merged by candidate/check IDs with deterministic reducers. Each node is
idempotent given its inputs so a resumed checkpoint can re-run an interrupted node safely.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from ..adapters import store as st
from ..adapters.external import linkup
from ..adapters.model_client import model_client
from ..config import settings
from ..domain import rules as R
from ..domain.models import CandidateOffer
from ..domain.ranking import evidence_coverage, rank, score_candidate, strip_internal
from ..domain.scheduler import build_plan, exposure_for
from .tools import BudgetExceeded, ToolRunner

CATEGORY_NODES = {
    "supplier_site_checks": {"supplier_site", "logistics"},
    "technical_checks": {"technical"},
    "regulatory_route": {"regulatory"},
}


def _pace(factor: float = 1.0) -> None:
    if settings.pacing_ms > 0:
        time.sleep(settings.pacing_ms * factor / 1000)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class InvestigationNodes:
    def __init__(self, services: Any):
        self.s = services

    # ------------------------------------------------------------------ helpers
    @property
    def cat(self):  # noqa: ANN201
        return self.s.catalog

    def tools(self, state: dict) -> ToolRunner:
        return ToolRunner(self.s.bus, state["run_id"], state["case_id"], state["generation_id"], settings.run_tool_budget)

    def emit(self, state: dict, type_: str, summary: str, data: Optional[dict] = None, task_id: Optional[str] = None, evidence_refs: Optional[list] = None) -> None:
        self.s.bus.publish(state["run_id"], state["case_id"], type_, summary, data or {}, task_id=task_id,
                           invocation_id=state["generation_id"], evidence_refs=evidence_refs or [])

    def task(self, state: dict, task_id: str, name: str, status: str, summary: Optional[str] = None, data: Optional[dict] = None) -> dict:
        typ = {"running": "task.started", "completed": "task.completed", "failed": "task.failed", "reused": "task.completed"}[status]
        self.emit(state, typ, summary or name, {"task": name, "status": status, **(data or {})}, task_id=task_id)
        return {task_id: {"task_id": task_id, "name": name, "status": status, "summary": summary, "at": _now_iso()}}

    def _ctx(self, state: dict, cid: str) -> R.CandidateContext:
        offer = state["offers"][cid]
        site = self.cat.sites[offer["site_id"]]
        route = self.cat.routes[offer["logistics_route_id"]]
        from ..domain.scheduler import signal_matches_route

        sigs = [s for s in state["signals"] if signal_matches_route(s, route, site)]
        comp = self.cat.component_for_case(state["case_id"])
        req_set = self.cat.requirement_sets[comp["requirement_set_id"]]
        return R.CandidateContext(
            case_id=state["case_id"], offer=offer, site=site, supplier=self.cat.suppliers[offer["supplier_id"]], route=route,
            component=comp, docs=state["docs"].get(cid, []), facts=state["facts"], now=datetime.fromisoformat(state["now"].replace("Z", "+00:00")),
            signals=sigs, applicability=self.cat.applicability, requirement_set=req_set,
        )

    def _affected(self, state: dict, cid: str) -> bool:
        aff = state.get("affected_candidate_ids")
        return aff is None or cid in aff

    # ------------------------------------------------------------------ nodes
    def load_case(self, state: dict) -> dict:
        case = self.s.store.get_case(state["run_id"], state["case_id"])
        prev = None
        if case["current_decision_id"]:
            row = self.s.store.get(st.decisions, case["current_decision_id"])
            prev = row["payload"] if row else None
        comp = self.cat.component_for_case(state["case_id"])
        label = "Reassessment" if state["kind"] == "reassessment" else "Investigation"
        self.emit(state, "case.started", f"{label} started for {comp['display_name']}",
                  {"kind": state["kind"], "trigger_id": state.get("trigger_id"), "input_revision": case["input_revision"], "mode": state["mode"]})
        if state["kind"] == "reassessment":
            self.emit(state, "reassessment.started", f"Reassessing affected outputs after {state.get('trigger_id') or 'change'}",
                      {"affected_candidate_ids": state.get("affected_candidate_ids"), "trigger_id": state.get("trigger_id")})
        tasks = self.task(state, "task-load", "Load case", "completed", f"Loaded {comp['display_name']} ({comp['part_identity']} rev {comp['revision']})")
        return {"input_revision": case["input_revision"], "prev_decision": prev, "tasks": tasks,
                "requirement_set_id": comp["requirement_set_id"]}

    def snapshot_requirements(self, state: dict) -> dict:
        tr = self.tools(state)
        with tr.call("get_requirement_set", "task-reqs", "Loading versioned requirement set", {"requirement_set_id": state["requirement_set_id"]}) as r:
            reqs = self.cat.requirements_for(state["requirement_set_id"])
            r["summary"] = f"{len(reqs)} requirements ({sum(1 for q in reqs if q['mandatory'])} mandatory) from {state['requirement_set_id']} v1"
            r["count"] = len(reqs)
        now = self.s.run_state.now(state["run_id"])
        signals = self.s.run_state.active_signals(state["run_id"], now)
        tasks = self.task(state, "task-reqs", "Snapshot requirements and active signals", "completed",
                          f"{len(reqs)} requirements; {len(signals)} active signal(s) read into the input snapshot",
                          {"active_signal_ids": [s["signal_id"] for s in signals]})
        _pace()
        return {"requirements": reqs, "now": now.isoformat(), "signals": signals, "tasks": tasks, "tool_usage": tr.usage}

    def _source(self, state: dict, route: str) -> dict:
        task_id = f"task-source-{route.lower()}"
        tasks = self.task(state, task_id, f"Source {route} options", "running")
        tr = self.tools(state)
        comp = self.cat.component_for_case(state["case_id"])
        with tr.call("query_candidate_offers", task_id, f"Querying {route} offer sources", {"route": route, "part": comp["part_identity"]}) as r:
            offers = [o for o in self.cat.offers_for_case(state["case_id"]) if o["route"] == route]
            r["summary"] = f"{len(offers)} {route} offer(s) from seeded supplier catalogue/replies adapter"
            r["count"] = len(offers)
            r["mode"] = "seeded_offers"
        leads: list[dict] = []
        prev_leads = (state.get("prev_decision") or {}).get("public_leads", {}).get(route) if state.get("prev_decision") else None
        if prev_leads is not None and state["kind"] == "reassessment":
            leads = prev_leads
        elif linkup.available:
            q = (f"{comp['display_name']} turbofan serviceable spare part supplier UK CAA Form 1" if route == "BUY"
                 else f"aerospace precision manufacturer UK Part 21G {comp['short_description'].split('.')[0]}")
            try:
                with tr.call("search_public_sources", task_id, f"Searching public sources (Linkup) for {route} leads", {"query": q}) as r:
                    res = linkup.search(q)
                    leads = [{**x, "route": route, "data_origin": "public_source", "eligibility": "not assessed — lead only",
                              "retrieved_at": res.get("retrieved_at")} for x in res.get("results", [])]
                    r["summary"] = (f"{len(leads)} public lead(s) via Linkup (context only; never eligible without evidence)" if res.get("ok")
                                    else f"Linkup unavailable: {res.get('detail', '')[:80]}")
                    r["count"] = len(leads)
                    r["mode"] = "linkup_search" if res.get("ok") else "linkup_failed"
            except BudgetExceeded:
                pass
        _pace()
        names = ", ".join(o["label"].split(" — ")[0] for o in offers)
        done = self.task(state, task_id, f"Source {route} options", "completed", f"{len(offers)} {route} candidate(s): {names}" if offers else f"No {route} candidates")
        return {"offers": {o["candidate_id"]: o for o in offers}, "public_leads": {route: leads}, "tasks": {**tasks, **done}, "tool_usage": tr.usage}

    def source_buy(self, state: dict) -> dict:
        return self._source(state, "BUY")

    def source_make(self, state: dict) -> dict:
        return self._source(state, "MAKE")

    def normalize_offers(self, state: dict) -> dict:
        normalised = {}
        for cid, o in state["offers"].items():
            normalised[cid] = CandidateOffer.model_validate(o).model_dump(mode="json")
        sup_site = {(o["supplier_id"], o["site_id"]) for o in normalised.values()}
        tasks = self.task(state, "task-normalise", "Normalise offers", "completed",
                          f"{len(normalised)} offers normalised to CandidateOffer across {len(sup_site)} supplier/site combinations "
                          f"({sum(1 for o in normalised.values() if o['route'] == 'BUY')} BUY, {sum(1 for o in normalised.values() if o['route'] == 'MAKE')} MAKE)")
        return {"offers": normalised, "tasks": tasks}

    def extract_and_validate(self, state: dict) -> dict:
        task_id = "task-extract"
        tasks = self.task(state, task_id, "Extract and validate evidence", "running")
        tr = self.tools(state)
        status = self.s.run_state.evidence_status(state["run_id"])
        docs: dict[str, list[dict]] = {}
        with tr.call("retrieve_evidence", task_id, "Retrieving governed evidence versions for each candidate", {"candidates": len(state["offers"])}) as r:
            for cid, o in state["offers"].items():
                docs[cid] = self.s.run_state.candidate_docs(state["run_id"], o, status)
            uniq = {d["version_id"]: d for ds in docs.values() for d in ds}
            r["summary"] = f"{len(uniq)} evidence versions resolved by exact ID from the authoritative snapshot"
            r["evidence_ids"] = sorted(uniq)
            r["mode"] = self.s.evidence_source
            r["count"] = len(uniq)
        for d in uniq.values():
            self.emit(state, "evidence.ingested", f"Evidence {d['title']}", {"version_id": d["version_id"], "hash": d["hash"], "doc_type": d["doc_type"],
                                                                          "data_origin": d["data_origin"]}, task_id=task_id, evidence_refs=[d["version_id"]])
        need = [d for d in uniq.values() if d["version_id"] not in state.get("facts", {})]
        facts: dict[str, dict] = {}
        modes: dict[str, str] = {}
        if need:
            with tr.call("extract_document_fields", task_id, f"Extracting typed fields from {len(need)} document(s)", {"documents": len(need)}) as r:
                out = self.s.extractor.extract(need)
                facts, modes = out["facts"], out["modes"]
                r["summary"] = (f"{len(need) - len(out['cached'])} extracted via {out['backend']}, {len(out['cached'])} deduplicated by content hash")
                r["mode"] = out["backend"]
                r["count"] = len(need)
        invalid = []
        for vid, ff in facts.items():
            bad = [f for f in ff.values() if f["validation_state"] != "valid"]
            invalid += [(vid, f["field"], f.get("validation_note")) for f in bad]
            self.emit(state, "evidence.extracted", f"{len(ff)} fact(s) from {self.cat.evidence[vid]['title']}",
                      {"version_id": vid, "facts": len(ff), "mode": modes.get(vid)}, task_id=task_id, evidence_refs=[vid])
        self.emit(state, "evidence.validated", f"Validated {sum(len(f) for f in facts.values())} facts in code; {len(invalid)} unusable value(s) flagged",
                  {"invalid": invalid[:40]}, task_id=task_id)
        _pace()
        done = self.task(state, task_id, "Extract and validate evidence", "completed",
                         f"{len(uniq)} documents, {sum(len(f) for f in facts.values())} new facts; {len(invalid)} unusable values kept as gaps")
        return {"docs": docs, "facts": facts, "extraction_modes": modes, "tasks": {**tasks, **done}, "tool_usage": tr.usage}

    def _run_checks(self, state: dict, node: str) -> dict:
        cats = CATEGORY_NODES[node]
        names = {"supplier_site_checks": "Supplier/site and logistics checks", "technical_checks": "Technical checks", "regulatory_route": "Regulatory route checks"}
        task_id = f"task-{node}"
        tasks = self.task(state, task_id, names[node], "running")
        tr = self.tools(state)
        prev_checks = {(c["candidate_id"], c["requirement_id"]): c for c in (state.get("prev_decision") or {}).get("checks", [])}
        checks: dict[str, dict] = {}
        counts = {"pass": 0, "fail": 0, "unknown": 0, "reused": 0}
        for cid, offer in sorted(state["offers"].items()):
            ctx = self._ctx(state, cid)
            per_candidate = []
            for req in state["requirements"]:
                if req["category"] not in cats or offer["route"] not in req["routes"]:
                    continue
                prev = prev_checks.get((cid, req["requirement_id"]))
                if not self._affected(state, cid) and prev:
                    c = dict(prev, reused_from_decision_id=prev.get("reused_from_decision_id") or state["prev_decision"]["decision_id"])
                    checks[c["check_id"]] = c
                    per_candidate.append(c)
                    counts["reused"] += 1
                    continue
                tool = "resolve_part_identity" if req["evaluator_id"] == "part_identity" else (
                    "match_signal_exposure" if req["evaluator_id"] == "route_viable" else "evaluate_requirement")
                with tr.call(tool, task_id, f"{req['title']} — {offer['label'].split(' — ')[0]}", {"candidate_id": cid, "requirement_id": req["requirement_id"]}, quiet=True) as r:
                    out = R.evaluate(ctx, req)
                    r["summary"] = out.result
                fp = R.check_fingerprint(req, out)
                if prev and prev.get("fingerprint") == fp:
                    c = dict(prev, reused_from_decision_id=prev.get("reused_from_decision_id") or state["prev_decision"]["decision_id"])
                    counts["reused"] += 1
                else:
                    c = {
                        "check_id": f"chk-{state['generation_id'][:8]}-{cid}-{req['requirement_id']}",
                        "case_id": state["case_id"], "candidate_id": cid, "requirement_id": req["requirement_id"],
                        "requirement_version": req["version"], "requirement_title": req["title"], "category": req["category"],
                        "mandatory": req["mandatory"], "result": out.result, "explanation": out.explanation,
                        "evidence_refs": out.evidence_refs, "fact_refs": out.fact_refs,
                        "input_versions": {**{e: self.cat.evidence[e]["hash"][:19] for e in out.evidence_refs if e in self.cat.evidence},
                                           **{f"signal:{k}": str(v) for k, v in out.signal_versions.items()}},
                        "dependency_ids": out.dependency_ids, "fingerprint": fp, "rule_version": f"{req['evaluator_id']}@{req['evaluator_version']}",
                        "evaluated_at": _now_iso(), "reused_from_decision_id": None, "contradictions": out.contradictions,
                        "feasible_if_unknown": out.feasible_if_unknown, "gap": out.gap, "template_code": req["template_code"],
                        "plain_language": req["plain_language"],
                    }
                    counts[out.result] += 1
                checks[c["check_id"]] = c
                per_candidate.append(c)
            if per_candidate:
                self.emit(state, "check.completed", f"{offer['label'].split(' — ')[0]}: " + ", ".join(
                    f"{c['requirement_title']} {c['result'].upper()}" for c in per_candidate)[:300],
                    {"candidate_id": cid, "category": sorted(cats), "checks": [{"check_id": c["check_id"], "requirement_id": c["requirement_id"],
                                                                               "result": c["result"], "reused": bool(c.get("reused_from_decision_id"))}
                                                                              for c in per_candidate]},
                    task_id=task_id, evidence_refs=sorted({e for c in per_candidate for e in c["evidence_refs"]})[:20])
        fallback = (f"{counts['pass']} pass, {counts['fail']} fail, {counts['unknown']} unknown"
                    + (f", {counts['reused']} reused unchanged" if counts["reused"] else ""))
        summary, origin = model_client.summarise(node, {"task": names[node], "results": [
            {"candidate": state["offers"][c["candidate_id"]]["label"], "check": c["requirement_title"], "result": c["result"], "why": c["explanation"]}
            for c in checks.values()][:40]}, fallback) if state["kind"] == "investigation" else (fallback, "deterministic")
        _pace()
        done = self.task(state, task_id, names[node], "completed", summary, {"counts": counts, "summary_origin": origin})
        return {"checks": checks, "tasks": {**tasks, **done}, "tool_usage": tr.usage}

    def supplier_site_checks(self, state: dict) -> dict:
        return self._run_checks(state, "supplier_site_checks")

    def technical_checks(self, state: dict) -> dict:
        return self._run_checks(state, "technical_checks")

    def regulatory_route(self, state: dict) -> dict:
        return self._run_checks(state, "regulatory_route")

    def resolve_gaps_if_budget(self, state: dict) -> dict:
        """FR-05 adaptive investigation: dispatch focused follow-ups for open gaps, rerun affected checks."""
        task_id = "task-gaps"
        tr = self.tools(state)
        checks = dict(state["checks"])
        gaps: dict[str, dict] = dict(state.get("gaps", {}))
        used: dict[str, int] = dict(state.get("followups_used", {}))
        new_docs = {k: list(v) for k, v in state["docs"].items()}
        new_facts: dict[str, dict] = {}
        open_checks = [c for c in checks.values() if c["mandatory"] and c["result"] == "unknown" and c.get("gap")
                       and self._affected(state, c["candidate_id"]) and not c.get("reused_from_decision_id")]
        if not open_checks:
            return {"tasks": self.task(state, task_id, "Resolve evidence gaps", "completed", "No open evidence gaps")}
        tasks = self.task(state, task_id, "Resolve evidence gaps", "running", f"{len(open_checks)} gap(s) open")
        replies = self.cat.supplier_replies
        resolved, exhausted = 0, 0
        by_candidate: dict[str, list[dict]] = {}
        for c in open_checks:
            by_candidate.setdefault(c["candidate_id"], []).append(c)
        for cid, cand_checks in sorted(by_candidate.items()):
            cand_checks.sort(key=lambda c: (c["gap"].get("priority", 9), c["requirement_id"]))
            for c in cand_checks:
                gid = f"gap-{state['run_id'][:8]}-{cid}-{c['requirement_id']}"
                gap = gaps.get(gid) or {"gap_id": gid, "case_id": state["case_id"], "candidate_id": cid, "site_id": state["offers"][cid]["site_id"],
                                        "requirement_id": c["requirement_id"], "desired": c["gap"]["desired"],
                                        "allowed_sources": c["gap"]["allowed_sources"], "priority": c["gap"].get("priority", 1),
                                        "status": "open", "attempts": []}
                if gid not in gaps:
                    self.emit(state, "gap.opened", f"Gap: {gap['desired']} ({state['offers'][cid]['label'].split(' — ')[0]})", gap, task_id=task_id)
                gaps[gid] = gap
                while gap["status"] == "open":
                    if used.get(cid, 0) >= settings.followup_attempts_per_candidate:
                        gap["status"] = "exhausted"
                        exhausted += 1
                        break
                    attempt = used.get(cid, 0) + 1
                    used[cid] = attempt
                    try:
                        with tr.call("request_supplier_followup", task_id, f"Follow-up {attempt}/{settings.followup_attempts_per_candidate} to supplier for {c['requirement_title']}",
                                     {"candidate_id": cid, "requirement_id": c["requirement_id"], "desired": gap["desired"]}) as r:
                            reply = next((x for x in replies if x["candidate_id"] == cid and x["requirement_id"] == c["requirement_id"]
                                          and x["attempt"] == len(gap["attempts"]) + 1), None)
                            msg = reply["message"] if reply else "No supplier response within the follow-up window (synthetic connector)."
                            gap["attempts"].append({"attempt": attempt, "at": _now_iso(), "outcome": "evidence" if reply and reply.get("evidence") else "none", "message": msg})
                            r["summary"] = msg
                            r["mode"] = "seeded_supplier_replies"
                            if reply and reply.get("evidence"):
                                ev = reply["evidence"]
                                self.s.run_state.activate_followup(state["run_id"], cid, ev["version_id"])
                                new_docs.setdefault(cid, []).append(dict(ev))
                                out = self.s.extractor.extract([ev])
                                new_facts.update(out["facts"])
                                r["evidence_ids"] = [ev["version_id"]]
                                self.emit(state, "evidence.ingested", f"Follow-up evidence received: {ev['title']}", {"version_id": ev["version_id"], "via": "gap follow-up"},
                                          task_id=task_id, evidence_refs=[ev["version_id"]])
                    except BudgetExceeded:
                        gap["status"] = "exhausted"
                        exhausted += 1
                        break
                    if gap["attempts"][-1]["outcome"] == "evidence":
                        # rerun the affected checks for this candidate with the new evidence
                        st_view = {**state, "docs": new_docs, "facts": {**state["facts"], **new_facts}}
                        ctx = self._ctx(st_view, cid)
                        for chk in [x for x in checks.values() if x["candidate_id"] == cid and x["result"] != "pass"]:
                            req = next(q for q in state["requirements"] if q["requirement_id"] == chk["requirement_id"])
                            out = R.evaluate(ctx, req)
                            if out.result != chk["result"] or out.evidence_refs != chk["evidence_refs"]:
                                checks[chk["check_id"]] = {**chk, "result": out.result, "explanation": out.explanation, "evidence_refs": out.evidence_refs,
                                                           "fact_refs": out.fact_refs, "dependency_ids": out.dependency_ids, "fingerprint": R.check_fingerprint(req, out),
                                                           "evaluated_at": _now_iso(), "gap": out.gap, "feasible_if_unknown": out.feasible_if_unknown,
                                                           "rerun_reason": f"follow-up evidence for {gid}"}
                        now_c = checks[c["check_id"]]
                        if now_c["result"] != "unknown":
                            gap["status"] = "resolved"
                            resolved += 1
                            self.emit(state, "gap.resolved", f"Gap resolved: {c['requirement_title']} now {now_c['result'].upper()} for "
                                      f"{state['offers'][cid]['label'].split(' — ')[0]}", {"gap_id": gid, "check_id": c["check_id"], "result": now_c["result"]},
                                      task_id=task_id, evidence_refs=now_c["evidence_refs"])
                if gap["status"] == "exhausted":
                    self.emit(state, "gap.opened", f"Gap remains pending after {len(gap['attempts'])} attempt(s): {gap['desired']}",
                              {**gap, "pending": True}, task_id=task_id)
        _pace()
        done = self.task(state, task_id, "Resolve evidence gaps", "completed",
                         f"{resolved} gap(s) resolved by targeted follow-up; {exhausted} left pending (budget {settings.followup_attempts_per_candidate}/candidate)")
        return {"checks": checks, "gaps": gaps, "followups_used": used, "docs": new_docs, "facts": new_facts,
                "tasks": {**tasks, **done}, "tool_usage": tr.usage}

    def evaluate_eligibility(self, state: dict) -> dict:
        elig = {}
        for cid in state["offers"]:
            cs = [c for c in state["checks"].values() if c["candidate_id"] == cid]
            e, feasible = R.eligibility_from(cs)
            elig[cid] = {"eligibility": e, "feasible": feasible}
        n = sum(1 for v in elig.values() if v["eligibility"] == "eligible")
        tasks = self.task(state, "task-eligibility", "Evaluate mandatory gates", "completed",
                          f"{n} eligible, {sum(1 for v in elig.values() if v['eligibility'] == 'pending')} pending, "
                          f"{sum(1 for v in elig.values() if v['eligibility'] == 'ineligible')} ineligible")
        return {"eligibility": elig, "tasks": tasks}

    def schedule_and_rank(self, state: dict) -> dict:
        task_id = "task-rank"
        tasks = self.task(state, task_id, "Schedule recovery plans and rank", "running")
        tr = self.tools(state)
        prev_cands = {c["candidate"]["candidate_id"]: c for c in (state.get("prev_decision") or {}).get("candidates", [])}
        rows = []
        for cid, offer in sorted(state["offers"].items()):
            site = self.cat.sites[offer["site_id"]]
            route = self.cat.routes[offer["logistics_route_id"]]
            prev = prev_cands.get(cid)
            if not self._affected(state, cid) and prev and prev.get("plan"):
                plan, exposure = prev["plan"], prev["exposure"]
            else:
                with tr.call("build_recovery_plan", task_id, f"Recovery plan — {offer['label'].split(' — ')[0]}", {"candidate_id": cid}, quiet=True) as r:
                    plan = build_plan(offer, self.cat.plans[cid], route, site, state["signals"], self.cat.fx)
                    r["summary"] = f"day {plan['finish_day']}"
                with tr.call("match_signal_exposure", task_id, "Exposure", {"candidate_id": cid}, quiet=True):
                    exposure = exposure_for(route, site, state["signals"])
            with tr.call("get_supplier_site_metrics", task_id, "Metrics", {"site_id": site["site_id"]}, quiet=True):
                otd_m = self.cat.metric(site["site_id"], "on_time_delivery_rate")
                ppm_m = self.cat.metric(site["site_id"], "quality_escapes_ppm")
            e = state["eligibility"][cid]
            score = score_candidate(state["case_id"], plan, otd_m["value"] if otd_m else None, exposure["value"], self.cat.ranking) if e["eligibility"] == "eligible" else None
            cand_checks = [c for c in state["checks"].values() if c["candidate_id"] == cid]
            gaps = [g for g in state.get("gaps", {}).values() if g["candidate_id"] == cid and g["status"] != "resolved"]
            rows.append({"candidate": offer, "eligibility": e["eligibility"], "feasible": e["feasible"], "score": score, "plan": plan,
                         "check_ids": sorted(c["check_id"] for c in cand_checks), "gaps": gaps,
                         "reliability": [m for m in (otd_m, ppm_m) if m], "exposure": exposure, "evidence_coverage": evidence_coverage(cand_checks),
                         "supplier": self.cat.suppliers[offer["supplier_id"]], "site": site})
        with tr.call("rank_eligible_offers", task_id, "Ranking eligible offers with the saved preference configuration",
                     {"ranking_config_version": self.cat.ranking["ranking_config_version"]}) as r:
            ranked = rank(rows)
            r["summary"] = "Order: " + (" > ".join(f"{x['candidate']['label'].split(' — ')[0]} ({x['score']['score']:.2f})" for x in ranked) or "no eligible offers")
        for row in rows:
            fails = [c for c in state["checks"].values() if c["candidate_id"] == row["candidate"]["candidate_id"] and c["mandatory"] and c["result"] != "pass"]
            if row["eligibility"] == "eligible":
                row["summary"] = (f"Rank {row['rank']}: ready by day {row['plan']['finish_day']:g}, £{float(row['plan']['landed_cost']['amount']):,.0f} landed, "
                                  f"score {row['score']['score']:.2f}")
            elif row["eligibility"] == "pending":
                row["summary"] = ("Feasible but not ready to select: " if row["feasible"] else "Pending evidence: ") + "; ".join(c["requirement_title"] for c in fails)
            else:
                row["summary"] = "Not eligible: " + "; ".join(f"{c['requirement_title']} failed" for c in fails if c["result"] == "fail")
            row["score"] = strip_internal(row["score"])
        _pace()
        best = ranked[0] if ranked else None
        done = self.task(state, task_id, "Schedule recovery plans and rank", "completed",
                         f"Preferred: {best['candidate']['label']} (day {best['plan']['finish_day']:g})" if best else "No eligible offer yet")
        return {"ranked": rows, "tasks": {**tasks, **done}, "tool_usage": tr.usage}

    def persist_decision(self, state: dict) -> dict:
        tr = self.tools(state)
        with tr.call("persist_decision", "task-persist", "Persisting immutable decision snapshot (compare-and-swap)", {"generation_id": state["generation_id"]}) as r:
            result = self.s.decisions.persist(state, tool_usage=self._sum_usage(state, tr.usage))
            r["summary"] = result["summary"]
        return {"decision_id": result["decision_id"], "decision_status": result["status"], "tool_usage": tr.usage,
                "tasks": self.task(state, "task-persist", "Persist decision", "completed", result["summary"])}

    @staticmethod
    def _sum_usage(state: dict, extra: dict) -> dict:
        total = dict(state.get("tool_usage", {}))
        for k, v in extra.items():
            total[k] = total.get(k, 0) + v
        return total
