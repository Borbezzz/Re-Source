"""DocumentService (PRD FR-13, AC-10/11/22): applicable document generation, versioned drafts and
packages with guarded publication, review/edit, stale handling and the simulated submission adapter.

Consistency rules
* Drafts and packages are immutable versions; the case row holds the transactional current pointer.
* Generation binds selection, evidence set, template registry version, starting package version and
  case revision into a stable generation_id and publishes only if those still match and no
  pending-change barrier exists; otherwise the result is kept as `superseded`.
* User edits create new draft + package versions and reset review; approval binds the exact package hash.
* Simulated submission validates everything inside one transaction; a stable operation key
  (package id, version, approved hash) makes retries return the same receipt.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any, Optional

from ..adapters import store as st
from ..adapters.renderer import render_package
from ..adapters.store import dumps, now_iso
from ..domain import documents as D
from ..domain.errors import DomainError, conflict, invalid, not_found, stale
from ..domain.models import DocumentPatchRequest, DocumentsView, SubmissionRequest


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


class DocumentService:
    def __init__(self, services: Any):
        self.s = services

    @property
    def store(self):  # noqa: ANN201
        return self.s.store

    @property
    def bus(self):  # noqa: ANN201
        return self.s.bus

    @property
    def catalog(self):  # noqa: ANN201
        return self.s.catalog

    # ------------------------------------------------------------------ helpers
    def _packages(self, run_id: str, case_id: str) -> list[dict]:
        return self.store.find(st.packages, run_id=run_id, case_id=case_id, order_by="version", desc=True)

    def _drafts_for(self, package: dict) -> list[dict]:
        out = []
        for did in package["draft_ids"]:
            row = self.store.get(st.drafts, did)
            if row:
                out.append(row["payload"])
        return out

    def _operator(self) -> dict:
        return self.catalog.scenario.get("operator", {})

    def _selection(self, selection_id: str) -> Optional[dict]:
        row = self.store.get(st.selections, selection_id)
        return row["payload"] if row else None

    def _decision(self, decision_id: str) -> dict:
        row = self.store.get(st.decisions, decision_id)
        if not row:
            raise not_found(f"decision {decision_id}")
        return row["payload"]

    # ------------------------------------------------------------------ generation
    def build_drafts(self, run_id: str, case_id: str, selection: dict, decision: dict, generation_id: str) -> tuple[dict, list[dict]]:
        plan = D.plan_package(decision, selection["candidate_id"], self.catalog)
        case_info = D.case_info_for(case_id, self.catalog)
        drafts = []
        rule = plan["rule"] or {}
        for item in plan["templates"]:
            tpl = item["template"]
            fields = D.autofill(tpl, decision, selection["candidate_id"], case_info, self.catalog, self._operator(), selection)
            rev = self.template_revisions(run_id).get(tpl["template_id"])
            drafts.append({
                "draft_id": f"draft-{uuid.uuid4().hex[:12]}",
                "case_id": case_id,
                "scenario_run_id": run_id,
                "template_id": tpl["template_id"],
                "template_version": tpl["version"] + (f" + {rev['revision']}" if rev else ""),
                "template_title": tpl["title"],
                "version": 1,
                "selection_id": selection["selection_id"],
                "generation_id": generation_id,
                "fields": fields,
                "validation": D.validate_draft(fields),
                "review_state": "draft",
                "status": "current",
                "why_included": item["why_included"],
                "applicability": {"rule_id": rule.get("rule_id"), "title": rule.get("title"), "explanation": plan["route_explanation"],
                                  "basis": rule.get("basis", []), "facts": plan["facts"], "authority_application": plan["authority_application"],
                                  "catalogue_version": self.catalog.applicability.get("catalogue_version")},
                "created_at": now_iso(),
            })
        return plan, drafts

    def template_revisions(self, run_id: str) -> dict:
        """Run-scoped template/applicability revisions activated through the change gateway (FR-13)."""
        return self.store.kv_get(f"template_revs:{run_id}") or {}

    def generate(self, run_id: str, case_id: str, selection_id: str) -> Optional[dict]:
        """Outbox consumer for op_type 'generate_documents'. Idempotent per generation_id."""
        with self.store.tx() as c:
            self.store.lock_run(c, run_id)
            case = self.store.lock_case(c, run_id, case_id)
            sel_row = self.store.get(st.selections, selection_id)
            if not sel_row or sel_row["status"] != "current" or case["current_selection_id"] != selection_id:
                return None  # selection no longer current: nothing to prepare
            selection = sel_row["payload"]
            decision = self._decision(selection["decision_id"])
            if case.get("current_package_id"):  # retry after a completed generation: return the published package
                cur = self.store.get(st.packages, case["current_package_id"])
                if cur and cur["status"] == "current" and cur["payload"]["selection_id"] == selection_id:
                    return cur["payload"]
            existing = self._packages(run_id, case_id)
            start_version = existing[0]["payload"]["version"] if existing else 0
            revs = sorted((k, v["revision"]) for k, v in self.template_revisions(run_id).items())
            gen_basis = f"{selection_id}|{decision.get('evidence_set_id')}|{self.catalog.templates_version}|{revs}|{start_version}|{case['revision']}"
            generation_id = "docgen-" + hashlib.sha256(gen_basis.encode()).hexdigest()[:16]
            dup = next((p for p in existing if p.get("generation_id") == generation_id), None)
            if dup:
                return dup["payload"]
            if case["state"] != "documents_preparing":
                self.store.update_case(c, run_id, case_id, state="documents_preparing", revision=case["revision"] + 1)
                self.bus.publish(run_id, case_id, "documents.preparing", "Preparing the applicable document package for the accepted option",
                                 {"selection_id": selection_id, "generation_id": generation_id, "decision_id": decision["decision_id"]})
            start_revision = self.store.lock_case(c, run_id, case_id)["revision"]
        # the pending-change barrier (run row) is re-checked inside the publication transaction below

        plan, drafts = self.build_drafts(run_id, case_id, selection, decision, generation_id)
        readiness = D.merge_readiness([d["validation"] for d in drafts])

        with self.store.tx() as c:
            run = self.store.lock_run(c, run_id)
            case = self.store.lock_case(c, run_id, case_id)
            sel_row = self.store.get(st.selections, selection_id)
            all_pk = self._packages(run_id, case_id)
            version = (all_pk[0]["payload"]["version"] if all_pk else 0) + 1
            publish = (sel_row is not None and sel_row["status"] == "current" and case["current_selection_id"] == selection_id
                       and case["revision"] == start_revision and int(run.get("barrier_count") or 0) == 0)
            status = "current" if publish else "superseded"
            for d in drafts:
                prev = self.store.find(st.drafts, run_id=run_id, case_id=case_id)
                d["version"] = 1 + sum(1 for p in prev if p["payload"]["template_id"] == d["template_id"])
                d["status"] = status
            package = {
                "package_id": f"pkg-{uuid.uuid4().hex[:12]}",
                "case_id": case_id,
                "scenario_run_id": run_id,
                "version": version,
                "selection_id": selection_id,
                "decision_id": decision["decision_id"],
                "generation_id": generation_id,
                "evidence_set_id": decision.get("evidence_set_id", ""),
                "draft_ids": [d["draft_id"] for d in drafts],
                "package_hash": D.package_hash(drafts),
                "review_state": "draft",
                "approved_hash": None,
                "readiness": readiness,
                "status": status,
                "destination_type": plan["destination_type"],
                "route_explanation": plan["route_explanation"],
                "created_at": now_iso(),
            }
            for d in drafts:
                self.store.put(st.drafts, d["draft_id"], run_id, d, case_id=case_id, status=status, package_id=package["package_id"], version=d["version"])
            self.store.put(st.packages, package["package_id"], run_id, package, case_id=case_id, status=status, version=version,
                           generation_id=generation_id)
            if publish:
                self._supersede_current(run_id, case_id, case.get("current_package_id"))
                self.store.update_case(c, run_id, case_id, current_package_id=package["package_id"], state="documents_ready",
                                       revision=case["revision"] + 1)
                n_tasks = len(readiness["completion_tasks"])
                self.bus.publish(run_id, case_id, "documents.ready",
                                 f"Document package v{version} ready: {len(drafts)} document(s), {len(readiness['blocking'])} blocking item(s), "
                                 f"{n_tasks} sign-off task(s)",
                                 {"package_id": package["package_id"], "version": version, "package_hash": package["package_hash"],
                                  "templates": [d["template_id"] for d in drafts], "destination_type": plan["destination_type"],
                                  "rule_id": (plan["rule"] or {}).get("rule_id"), "readiness": readiness},
                                 evidence_refs=sorted({e for d in drafts for f in d["fields"] for e in f["provenance"]["evidence_refs"]})[:30])
        return package

    def _supersede_current(self, run_id: str, case_id: str, package_id: Optional[str], keep_draft_ids: tuple = ()) -> None:
        if not package_id:
            return
        row = self.store.get(st.packages, package_id)
        if not row or row["status"] != "current":
            return
        self.store.set_status(st.packages, package_id, "superseded")
        for did in row["payload"]["draft_ids"]:
            if did not in keep_draft_ids:
                d = self.store.get(st.drafts, did)
                if d and d["status"] == "current":
                    self.store.set_status(st.drafts, did, "superseded")

    # ------------------------------------------------------------------ view
    def view(self, run_id: str, case_id: str) -> dict:
        case = self.store.get_case(run_id, case_id)
        if not case:
            raise not_found(f"case {case_id}")
        pk_rows = self._packages(run_id, case_id)
        current = None
        if case.get("current_package_id"):
            row = self.store.get(st.packages, case["current_package_id"])
            current = row["payload"] if row else None
        drafts = self._drafts_for(current) if current else []
        receipts = [r["payload"] for r in self.store.find(st.receipts, run_id=run_id, case_id=case_id, order_by="created_at", desc=True)]
        if case["state"] == "documents_preparing":
            gen = "preparing"
        elif current is None:
            gen = "none"
        elif current["status"] == "stale" or case["state"] == "documents_stale":
            gen = "stale"
        else:
            gen = "ready"
        templates = []
        if current:
            for d in drafts:
                tpl = self.catalog.templates.get(d["template_id"])
                if tpl:
                    templates.append(D.form_template_view(tpl, d.get("why_included")))
        view = {
            "case_id": case_id,
            "current_package": current,
            "current_drafts": drafts,
            "history": [r["payload"] for r in pk_rows],
            "receipts": receipts,
            "generation_status": gen,
            "readiness": current["readiness"] if current else {"ready": False, "blocking": [], "completion_tasks": [], "note": "No package yet"},
            "templates": templates,
        }
        return DocumentsView.model_validate(view).model_dump(mode="json")

    # ------------------------------------------------------------------ edits / review
    def patch(self, run_id: str, target_id: str, req: dict) -> dict:
        r = DocumentPatchRequest.model_validate(req)
        draft_row = self.store.get(st.drafts, target_id)
        pkg_row = None
        if draft_row:
            case_id = draft_row["case_id"]
        else:
            pkg_row = self.store.get(st.packages, target_id)
            if not pkg_row:
                raise not_found(f"document {target_id}")
            case_id = pkg_row["case_id"]
        if (draft_row or pkg_row)["run_id"] != run_id:
            raise not_found(f"document {target_id} in run {run_id}")
        with self.store.tx() as c:
            case = self.store.lock_case(c, run_id, case_id)
            cur_id = case.get("current_package_id")
            cur_row = self.store.get(st.packages, cur_id) if cur_id else None
            if not cur_row:
                raise conflict("PACKAGE_STALE", "No current document package for this case", case_revision=case["revision"])
            package = cur_row["payload"]
            if pkg_row and pkg_row["id"] != cur_id:
                raise conflict("PACKAGE_STALE", "This package version is no longer current", case_revision=case["revision"],
                               current_package_id=cur_id, current_version=package["version"])
            if draft_row and draft_row["id"] not in package["draft_ids"]:
                raise conflict("PACKAGE_STALE", "This draft version is no longer part of the current package", case_revision=case["revision"],
                               current_package_id=cur_id, current_version=package["version"])
            if package["status"] != "current":
                raise conflict("PACKAGE_STALE", f"Current package is {package['status']}; regenerate after reselection", case_revision=case["revision"])
            if r.expected_version != package["version"]:
                raise conflict("VERSION_CONFLICT", f"Expected package version {r.expected_version}, current is {package['version']}",
                               case_revision=case["revision"], current_version=package["version"])
            drafts = {d["draft_id"]: d for d in self._drafts_for(package)}
            changed_summary = []
            if r.field_edits:
                edits_by_draft: dict[str, dict] = {}
                for key, val in r.field_edits.items():
                    if draft_row:
                        edits_by_draft.setdefault(draft_row["id"], {})[key] = val
                    else:
                        tid, _, fid = key.partition(".")
                        did = next((d["draft_id"] for d in drafts.values() if d["template_id"] == tid), None)
                        if not did or not fid:
                            raise invalid(f"field edit key '{key}' must be '<template_id>.<field_id>' for package-level edits")
                        edits_by_draft.setdefault(did, {})[fid] = val
                new_ids = list(package["draft_ids"])
                for did, edits in edits_by_draft.items():
                    old = drafts[did]
                    fields = [dict(f, provenance=dict(f["provenance"])) for f in old["fields"]]
                    for fid, val in edits.items():
                        f = next((x for x in fields if x["field_id"] == fid), None)
                        if f is None:
                            raise invalid(f"unknown field {fid} on {old['template_id']}")
                        if not f.get("editable", True):
                            raise invalid(f"field {fid} on {old['template_id']} is not editable")
                        f["value"] = val if val not in ("",) else None
                        f["status"] = "filled" if f["value"] is not None else ("completion_task" if f["provenance"]["origin"] == "completion_task" else "missing")
                        f["provenance"].update(origin="user_edit", edited_by=r.actor, edited_at=now_iso(),
                                               transform=f"user edit (was: {f['provenance'].get('transform')})")
                        f["note"] = f"Edited by {r.actor}" + (f"; previous value retained in draft v{old['version']}" if old else "")
                    new = dict(old, draft_id=f"draft-{uuid.uuid4().hex[:12]}", version=old["version"] + 1, fields=fields,
                               validation=D.validate_draft(fields), review_state="draft", status="current", created_at=now_iso())
                    self.store.put(st.drafts, new["draft_id"], run_id, new, case_id=case_id, status="current", package_id=None, version=new["version"])
                    self.store.set_status(st.drafts, did, "superseded")
                    new_ids[new_ids.index(did)] = new["draft_id"]
                    drafts.pop(did)
                    drafts[new["draft_id"]] = new
                    changed_summary.append(f"{old['template_id']}: {', '.join(edits)}")
                ordered = [drafts[i] for i in new_ids]
                all_pk = self._packages(run_id, case_id)
                version = all_pk[0]["payload"]["version"] + 1
                new_pkg = dict(package, package_id=f"pkg-{uuid.uuid4().hex[:12]}", version=version, draft_ids=new_ids,
                               package_hash=D.package_hash(ordered), review_state="draft", approved_hash=None,
                               readiness=D.merge_readiness([d["validation"] for d in ordered]), status="current", created_at=now_iso(),
                               generation_id=f"edit-{package['generation_id']}-v{version}")
                self.store.set_status(st.packages, package["package_id"], "superseded")
                for did in new_ids:  # reuse unchanged drafts by reference; point new drafts at their package
                    row = self.store.get(st.drafts, did)
                    if row and row.get("package_id") is None:
                        self.store.put(st.drafts, did, run_id, row["payload"], case_id=case_id, status="current", package_id=new_pkg["package_id"],
                                       version=row["payload"]["version"])
                self.store.put(st.packages, new_pkg["package_id"], run_id, new_pkg, case_id=case_id, status="current", version=version,
                               generation_id=new_pkg["generation_id"])
                package = new_pkg
                self.store.update_case(c, run_id, case_id, current_package_id=package["package_id"])
            if r.review_action:
                state = {"submit_for_review": "in_review", "approve": "approved", "request_changes": "changes_requested"}[r.review_action]
                targets = list(package["draft_ids"]) if (pkg_row or not draft_row) else [self._current_draft_id(package, draft_row, drafts)]
                for did in targets:
                    d = drafts[did]
                    d["review_state"] = state
                    self.store.put(st.drafts, did, run_id, d, case_id=case_id, status=d["status"], version=d["version"],
                                   package_id=(self.store.get(st.drafts, did) or {}).get("package_id"))
                ordered = [drafts[i] for i in package["draft_ids"]]
                all_approved = all(d["review_state"] == "approved" for d in ordered)
                package = dict(package, review_state="approved" if all_approved else "draft",
                               approved_hash=package["package_hash"] if all_approved else None)
                self.store.put(st.packages, package["package_id"], run_id, package, case_id=case_id, status=package["status"],
                               version=package["version"], generation_id=package["generation_id"])
                changed_summary.append(f"review: {r.review_action} ({len(targets)} document(s))")
            case_now = self.store.lock_case(c, run_id, case_id)
            new_state = "documents_ready" if case_now["state"] in ("documents_ready", "documents_preparing") else case_now["state"]
            self.store.update_case(c, run_id, case_id, revision=case_now["revision"] + 1, state=new_state)
            self.bus.publish(run_id, case_id, "documents.ready",
                             f"Document package v{package['version']} updated — " + "; ".join(changed_summary or ["no change"]),
                             {"package_id": package["package_id"], "version": package["version"], "package_hash": package["package_hash"],
                              "review_state": package["review_state"], "approved_hash": package["approved_hash"], "actor": r.actor,
                              "readiness": package["readiness"]})
            rev = case_now["revision"] + 1
        return {"package": package, "drafts": [drafts[i] for i in package["draft_ids"]], "case_revision": rev}

    @staticmethod
    def _current_draft_id(package: dict, draft_row: dict, drafts: dict) -> str:
        if draft_row["id"] in package["draft_ids"]:
            return draft_row["id"]
        tid = draft_row["payload"]["template_id"]
        return next(i for i in package["draft_ids"] if drafts[i]["template_id"] == tid)

    # ------------------------------------------------------------------ invalidation
    def mark_stale(self, conn: Any, run_id: str, case_id: str, reason: str) -> list[str]:
        """Inside the caller's transaction. Does not bump the case revision (the caller's fan-out does)."""
        case = self.store.lock_case(conn, run_id, case_id)
        pid = case.get("current_package_id")
        if not pid:
            return []
        row = self.store.get(st.packages, pid)
        if not row or row["status"] != "current":
            return []
        ids = [pid]
        readiness = dict(row["payload"].get("readiness") or {}, ready=False, stale_reason=reason)
        self.store.set_status(st.packages, pid, "stale", {"readiness": readiness})
        for did in row["payload"]["draft_ids"]:
            d = self.store.get(st.drafts, did)
            if d and d["status"] == "current":
                self.store.set_status(st.drafts, did, "stale")
                ids.append(did)
        if case["state"] in ("selected", "documents_preparing", "documents_ready"):
            self.store.update_case(conn, run_id, case_id, state="documents_stale")
        self.bus.publish(run_id, case_id, "documents.stale", f"Document package v{row['payload']['version']} is stale: {reason}",
                         {"package_id": pid, "draft_ids": ids[1:], "reason": reason,
                          "receipts_kept_historical": [r["id"] for r in self.store.find(st.receipts, run_id=run_id, case_id=case_id)]})
        return ids

    # ------------------------------------------------------------------ simulated submission
    def submit(self, run_id: str, case_id: str, req: dict) -> dict:
        r = SubmissionRequest.model_validate(req)
        pkg_row = self.store.get(st.packages, r.package_id)
        if not pkg_row or pkg_row["run_id"] != run_id or pkg_row["case_id"] != case_id:
            raise not_found(f"package {r.package_id}")
        pkg = pkg_row["payload"]
        op_key = f"{pkg['package_id']}:{pkg['version']}:{pkg.get('approved_hash')}"
        dup = self.store.find(st.receipts, run_id=run_id, operation_key=op_key)
        if dup:
            return dup[0]["payload"]
        with self.store.tx() as c:
            run = self.store.lock_run(c, run_id)
            case = self.store.lock_case(c, run_id, case_id)
            rev = case["revision"]
            dup = self.store.find(st.receipts, run_id=run_id, operation_key=op_key)
            if dup:
                return dup[0]["payload"]
            if int(run.get("barrier_count") or 0) > 0:
                raise DomainError(409, "BARRIER_ACTIVE", "A change is being registered for this run; retry after it is applied",
                                  retryable=True, case_revision=rev)
            sel_row = self.store.get(st.selections, r.selection_id)
            if (not sel_row or sel_row["status"] != "current" or case.get("current_selection_id") != r.selection_id
                    or pkg["selection_id"] != r.selection_id):
                raise stale("Selection is no longer current; reconfirm the current decision before submitting", case_revision=rev,
                            current_selection_id=case.get("current_selection_id"))
            pkg = self.store.get(st.packages, r.package_id)["payload"]
            if pkg["status"] != "current" or case.get("current_package_id") != r.package_id or pkg["version"] != r.package_version:
                raise conflict("PACKAGE_STALE", "Package version is not current; review the regenerated package", case_revision=rev,
                               current_package_id=case.get("current_package_id"))
            if pkg["review_state"] != "approved" or pkg.get("approved_hash") != pkg["package_hash"]:
                raise conflict("PACKAGE_NOT_APPROVED", "Package must be approved in review at its exact current hash", case_revision=rev,
                               package_hash=pkg["package_hash"], approved_hash=pkg.get("approved_hash"))
            drafts = self._drafts_for(pkg)
            if D.package_hash(drafts) != pkg["package_hash"]:
                raise conflict("PACKAGE_STALE", "Package content no longer matches its hash", case_revision=rev)
            readiness = D.merge_readiness([D.validate_draft(d["fields"]) for d in drafts])
            if readiness["blocking"]:
                raise DomainError(422, "NOT_READY", "Required fields are missing or invalid", case_revision=rev,
                                  details={"blocking": readiness["blocking"]})
            op_key = f"{pkg['package_id']}:{pkg['version']}:{pkg['approved_hash']}"
            payload_hash = _sha(dumps({"package": pkg, "fields": {d["draft_id"]: [[f["field_id"], f.get("value")] for f in d["fields"]] for d in drafts}}))
            receipt = {
                "receipt_id": f"rcpt-sim-{uuid.uuid4().hex[:12]}",
                "case_id": case_id,
                "scenario_run_id": run_id,
                "selection_id": r.selection_id,
                "package_id": pkg["package_id"],
                "package_version": pkg["version"],
                "package_hash": pkg["package_hash"],
                "destination_type": pkg["destination_type"],
                "destination_label": D.DESTINATION_LABELS.get(pkg["destination_type"], pkg["destination_type"]),
                "submitted_documents": [{"template_id": d["template_id"], "title": d["template_title"], "version": d["template_version"],
                                         "draft_id": d["draft_id"], "draft_version": d["version"], "hash": D.draft_hash(d),
                                         "completion_tasks": [t["label"] for t in D.validate_draft(d["fields"])["completion_tasks"]]} for d in drafts],
                "payload_hash": payload_hash,
                "idempotency_key": r.idempotency_key or op_key,
                "status": "accepted_simulated",
                "simulated_at": now_iso(),
                "label": "SIMULATED — no real submission was made",
            }
            for old in self.store.find(st.receipts, run_id=run_id, case_id=case_id):
                if old["status"] == "accepted_simulated":
                    self.store.set_status(st.receipts, old["id"], "historical")
            self.store.put(st.receipts, receipt["receipt_id"], run_id, receipt, case_id=case_id, status="accepted_simulated",
                           idem_key=receipt["idempotency_key"], operation_key=op_key)
            self.store.update_case(c, run_id, case_id, latest_receipt_id=receipt["receipt_id"], state="submission_simulated",
                                   visual_state="replacement_ready", revision=rev + 1)
            self.store.put(st.outbox, f"op-{uuid.uuid4().hex[:12]}", run_id, {"receipt_id": receipt["receipt_id"], "run_id": run_id, "case_id": case_id},
                           case_id=case_id, status="pending", op_type="project_receipt", attempts=0, available_at=now_iso(), last_error=None)
            self.bus.publish(run_id, case_id, "submission.simulated",
                             f"Simulated submission accepted: receipt {receipt['receipt_id']} ({receipt['destination_label']})",
                             {"receipt_id": receipt["receipt_id"], "package_id": pkg["package_id"], "package_version": pkg["version"],
                              "destination_type": receipt["destination_type"], "payload_hash": payload_hash, "simulated": True,
                              "completion_tasks": readiness["completion_tasks"]})
        return receipt

    # ------------------------------------------------------------------ rendering
    def render_package_html(self, run_id: str, package_id: str) -> str:
        row = self.store.get(st.packages, package_id)
        if not row or row["run_id"] != run_id:
            raise not_found(f"package {package_id}")
        pkg = row["payload"]
        drafts = self._drafts_for(pkg)
        receipt = next((x["payload"] for x in self.store.find(st.receipts, run_id=run_id, case_id=pkg["case_id"])
                        if x["payload"]["package_id"] == package_id), None)
        title = D.case_info_for(pkg["case_id"], self.catalog)["display_name"]
        return render_package(pkg, drafts, self.catalog.templates, receipt, case_title=title)
