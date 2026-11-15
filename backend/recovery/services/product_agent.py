"""A durable sourcing mandate, with a deliberately simulated mailbox transport.

Every continuation re-reads the owned project under its row lock. Research remains
fan-out queue work; RFQ selection, draft and demo messages commit together. No
function in this module can send email, approve an order or transfer money.
"""
from __future__ import annotations

import copy
import hashlib
import uuid

from ..adapters import store as st
from ..domain.errors import conflict, invalid
from ..domain.products import ProductPart
from ..runtime.tracing import span
from .product_workers import requirement_value


def _business_id(*values: str) -> str:
    return hashlib.sha256("|".join(values).encode()).hexdigest()[:24]


class ProductAgent:
    def _pause_agent_for_change(self, p: dict, message: str, *, inputs_changed: bool = False) -> None:
        agent = p.get("agent")
        if not agent:
            return
        agent.update(status="needs_attention" if inputs_changed else "paused", summary=message, updated_at=st.now_iso(),
                     attention=[{"code": "inputs_changed" if inputs_changed else "manual_change", "message": message, "part_ids": []}])
        self._event(p, "agent.interrupted", message)

    def _queue_agent_continuation(self, p: dict, cause: str) -> str | None:
        agent = p.get("agent")
        if not agent or agent["status"] not in {"queued", "running"} or agent["input_version"] != p["input_version"]:
            return None
        jid = "agent-" + _business_id(p["project_id"], agent["run_id"], str(agent["input_version"]), cause)
        self._prepare(p, "product_agent", {"run_id": agent["run_id"], "input_version": agent["input_version"], "continuation": cause}, jid)
        self.s.store.after_commit(lambda: self._dispatch(jid))
        return jid

    def agent_start(self, project_id: str, expected_version: int, mode: str) -> dict:
        with self._mutate(project_id) as p:
            prior = p.get("agent")
            if (prior and prior["input_version"] == p["input_version"] and prior["mode"] == mode
                    and p.get("_agent_start_version") == expected_version):
                return self._public(p)  # Lost HTTP response / duplicate command, not a new mandate.
            if p["version"] != expected_version:
                raise conflict("PRODUCT_CHANGED", "The project changed. Refresh before starting the agent.")
            if prior and prior["status"] in {"queued", "running"}:
                raise conflict("AGENT_RUNNING", "A sourcing agent is already working on this project.")
            if mode not in {"demo", "live"} or mode == "demo" and not p["demo_id"]:
                raise invalid("Sample supplier outreach is available only for prepared demo products.")
            now = st.now_iso()
            p["agent"] = {"run_id": f"agent-run-{uuid.uuid4().hex[:16]}", "input_version": p["input_version"], "mode": mode,
                          "status": "queued", "stage": "requirements", "summary": "Sourcing agent queued: check specifications, research suppliers and prepare nonbinding quote requests.",
                          "mandate": {"objective": "source_and_request_quotes", "outreach": "demo_mailbox" if mode == "demo" else "draft_only", "purchase_authorized": False},
                          "attention": [], "targets": [], "sent_count": 0, "reply_count": 0, "created_at": now, "updated_at": now}
            p.setdefault("mailbox", [])
            p["_agent_start_version"] = expected_version
            p["_agent_research_jobs"] = {}
            p["_agent_extraction_started"] = False
            p["_agent_resume_sequence"] = 0
            self._event(p, "agent.started", "Sourcing mandate accepted. Routine quote requests use the demo mailbox; purchasing is not authorized." if mode == "demo" else
                        "Sourcing mandate accepted. Research and RFQ drafting can proceed; external delivery needs a verified recipient and transport.")
            self._queue_agent_continuation(p, "start")
        return self.get(project_id)

    def _agent_control(self, p: dict, expected_run_id: str, expected_version: int, *, allow_progress: bool = False) -> dict:
        stale = expected_version > p["version"] if allow_progress else p["version"] != expected_version
        if stale or not p.get("agent") or p["agent"]["run_id"] != expected_run_id:
            raise conflict("AGENT_CHANGED", "The sourcing run changed. Refresh before controlling it.")
        return p["agent"]

    def agent_pause(self, project_id: str, expected_run_id: str, expected_version: int) -> dict:
        with self._mutate(project_id) as p:
            agent = self._agent_control(p, expected_run_id, expected_version, allow_progress=True)
            if agent["status"] in {"queued", "running"}:
                agent.update(status="paused", summary="Sourcing agent paused. In-flight research may finish, but no further RFQs or mailbox messages will be published.", updated_at=st.now_iso())
                self._event(p, "agent.paused", agent["summary"])
        return self.get(project_id)

    def agent_resume(self, project_id: str, expected_run_id: str, expected_version: int) -> dict:
        with self._mutate(project_id) as p:
            agent = self._agent_control(p, expected_run_id, expected_version)
            if agent["input_version"] != p["input_version"]:
                raise conflict("AGENT_INPUTS_CHANGED", "Specifications changed. Start a new sourcing run for the current inputs.")
            if agent["status"] not in {"paused", "needs_attention", "failed"}:
                return self._public(p)
            agent.update(status="queued", attention=[], summary="Sourcing agent resumed under the existing mandate.", updated_at=st.now_iso())
            # A user-requested retry may rerun failed discovery, never duplicate completed deliveries.
            failed = [r["part_id"] for r in p["research"] if r["status"] == "failed" and r["part_id"] in p.get("_agent_research_jobs", {})]
            if failed:
                for jid in self._queue_research(p, failed, agent["mode"]):
                    job = self.s.store.kv_get(f"job:{jid}")
                    p["_agent_research_jobs"][job["payload"]["part_id"]] = jid
                    self.s.store.after_commit(lambda job_id=jid: self._dispatch(job_id))
            p["_agent_resume_sequence"] = p.get("_agent_resume_sequence", 0) + 1
            self._event(p, "agent.resumed", agent["summary"])
            self._queue_agent_continuation(p, f"resume:{p['_agent_resume_sequence']}")
        return self.get(project_id)

    @staticmethod
    def _attention(p: dict, issues: list[dict], summary: str) -> None:
        p["agent"].update(status="needs_attention", attention=issues, summary=summary, updated_at=st.now_iso())

    @staticmethod
    def _part_spec(part: dict) -> dict:
        part = copy.deepcopy(part)
        for key in ("status", "confirmation_origin", "identity_source", "quantity_source", "part_number_source"):
            part.pop(key, None)
        for req in part["requirements"]:
            req.pop("status", None)
        return part

    def _accept_agent_requirements(self, p: dict) -> list[dict]:
        from .product_grounding import grounded_part_issues
        if not p["parts"]:
            return [{"code": "requirements_missing", "message": "Upload a bill of materials or specification with part names, explicit quantities and requirements.", "part_ids": []}]
        profile = self._profiles().get(p["demo_id"], {})
        defaults = {part["part_id"]: ProductPart.model_validate(part).model_dump(mode="json") for part in profile.get("parts", [])}
        proposed = [part for part in p["parts"] if part["status"] != "confirmed"]
        provided_sources = any(doc["data_origin"] == "provided_document" and doc["kind"] != "model" for doc in p["documents"])
        custom = [part for part in proposed if provided_sources or part["part_id"] not in defaults or self._part_spec(part) != self._part_spec(defaults[part["part_id"]])]
        issues = grounded_part_issues(p, custom) if custom else []
        if any(not part["requirements"] for part in p["parts"]):
            issues.append({"code": "requirements_missing", "message": "Each part needs an explicit sourcing requirement before research.",
                           "part_ids": [part["part_id"] for part in p["parts"] if not part["requirements"]]})
        if issues:
            return issues
        self._validate_sources(p, p["parts"])
        for part in proposed:
            part.update(status="confirmed", confirmation_origin="agent_grounded")
            for requirement in part["requirements"]:
                requirement["status"] = "confirmed"
        if proposed:
            self._event(p, "requirements.agent_verified", f"Agent verified {len(proposed)} parts against explicit source facts. This records agent verification, not human engineering approval.")
        return []

    def run_agent(self, project_id: str, run_id: str, input_version: int, continuation: str = "start") -> None:
        with span("product.sourcing_agent", inputs={"project_id": project_id, "run_id": run_id, "continuation": continuation}):  # noqa: SIM117 - outer tracing includes transaction publication
            with self._mutate(project_id) as p:
                agent = p.get("agent")
                if (not agent or agent["run_id"] != run_id or agent["input_version"] != input_version or p["input_version"] != input_version
                        or agent["status"] not in {"queued", "running"}):
                    return
                agent.update(status="running", updated_at=st.now_iso())
                provided_sources = any(d["data_origin"] == "provided_document" and d["kind"] != "model" for d in p["documents"])
                needs_extraction = not p["parts"] or provided_sources and any(part["status"] != "confirmed" and not part.get("identity_source") for part in p["parts"])
                if needs_extraction and any(d["kind"] != "model" for d in p["documents"]) and not p.get("_agent_extraction_started"):
                    jid = f"agent-extract-{run_id}"
                    p["_agent_extraction_started"] = True
                    p["_extract_job"] = jid
                    p["status"] = "extracting"
                    agent.update(stage="requirements", summary="Reading uploaded sources and discovering explicit parts and quantities.")
                    self._prepare(p, "product_extract", {"job_id": jid, "input_version": input_version}, jid)
                    self.s.store.after_commit(lambda: self._dispatch(jid))
                    self._event(p, "agent.extracting", agent["summary"])
                    return
                if p.get("_extract_job"):
                    return  # Extraction completion publishes the continuation transactionally.
                if issues := self._accept_agent_requirements(p):
                    self._attention(p, issues, "Some source facts need clarification before sourcing can continue.")
                    self._event(p, "agent.needs_attention", p["agent"]["summary"])
                    return
                if not p.get("_agent_research_jobs"):
                    for jid in self._queue_research(p, [part["part_id"] for part in p["parts"]], agent["mode"]):
                        job = self.s.store.kv_get(f"job:{jid}")
                        p["_agent_research_jobs"][job["payload"]["part_id"]] = jid
                        self.s.store.after_commit(lambda job_id=jid: self._dispatch(job_id))
                    # Existing in-flight manual discovery may be reused under this mandate.
                    for result in p["research"]:
                        p["_agent_research_jobs"].setdefault(result["part_id"], result["job_id"])
                    agent.update(stage="research", summary=f"Researching suppliers for {len(p['_agent_research_jobs'])} parts concurrently.")
                    self._event(p, "agent.researching", agent["summary"])
                    return
                results = [r for r in p["research"] if p["_agent_research_jobs"].get(r["part_id"]) == r["job_id"]]
                if any(r["status"] in {"queued", "running"} for r in results):
                    done = sum(r["status"] == "complete" for r in results)
                    agent.update(stage="research", summary=f"Supplier research complete for {done} of {len(results)} parts.")
                    return
                issues = []
                if len(results) != len(p["parts"]):
                    issues.append({"code": "research_changed", "message": "The current supplier investigations differ from this mandate. Start a new sourcing run.", "part_ids": []})
                targets, candidates = [], {}
                for result in results:
                    usable = [c for c in result["candidates"] if c["data_origin"] == ("synthetic_demo" if agent["mode"] == "demo" else "public_web")
                              and not any(e["status"] == "conflict" for e in c["evidence"])]
                    if result["status"] != "complete" or not usable:
                        issues.append({"code": "research_failed" if result["status"] == "failed" else "no_candidates", "message": "Supplier research needs another attempt or a clarified specification for this part.", "part_ids": [result["part_id"]]})
                        continue
                    same_currency = len({c.get("currency") for c in usable if c.get("price") is not None}) == 1
                    if agent["mode"] == "demo" and same_currency:
                        usable.sort(key=lambda c: (c.get("price") is None, c.get("price") or 0, c.get("lead_time_days") is None, c.get("lead_time_days") or 0, c["candidate_id"]))
                        reason = "Lowest listed sample price among same-currency demo offers; ask for a quotation and supporting evidence. Compliance remains unverified."
                    else:
                        reason = "Cited discovery lead chosen for a nonbinding quotation and missing-evidence request. Suitability and compliance remain unverified."
                    candidate = usable[0]
                    candidates[result["part_id"]] = candidate
                    targets.append({"part_id": result["part_id"], "candidate_id": candidate["candidate_id"], "reason": reason,
                                    "readiness": "demo_ready" if agent["mode"] == "demo" else "contact_required"})
                agent.update(stage="shortlist", targets=targets)
                if not targets:
                    self._attention(p, issues, "No suitable RFQ target is ready. Review the research issues or retry.")
                    self._event(p, "agent.needs_attention", agent["summary"])
                    return
                self._event(p, "agent.shortlisted", f"Selected {len(targets)} targets for nonbinding quote requests; no supplier has been certified eligible.")
                p["selections"] = {target["part_id"]: target["candidate_id"] for target in targets}
                p["package"] = self._agent_rfq_package(p, candidates)
                p["status"] = "packaged"
                agent["stage"] = "rfq"
                self._event(p, "agent.rfq_drafted", f"Drafted {len(targets)} quote requests with source specifications and open evidence questions.")
                if agent["mode"] == "live":
                    issues.append({"code": "contact_required", "message": "RFQs are drafted. External email delivery needs a verified recipient and a configured, authorized mailbox. No message has been sent.", "part_ids": [t["part_id"] for t in targets]})
                    self._attention(p, issues, "Quote requests are drafted; verified delivery details are needed.")
                    self._event(p, "agent.needs_attention", agent["summary"])
                    return
                agent["stage"] = "outreach"
                self._simulate_agent_mailbox(p, candidates)
                if issues:
                    self._attention(p, issues, "Sample quotes are ready for the available parts; other parts need attention.")
                else:
                    agent.update(status="recommendation_ready", stage="complete", attention=[], completed_at=st.now_iso(),
                                 summary=f"Recommendation ready: {agent['reply_count']} labelled sample quotes received in the demo mailbox. Review the evidence gaps before any purchasing decision.")
                self._event(p, "agent.recommendation_ready" if not issues else "agent.needs_attention", agent["summary"])

    @staticmethod
    def _agent_rfq_package(p: dict, candidates: dict) -> dict:
        agent = p["agent"]
        items = []
        for part in p["parts"]:
            candidate = candidates.get(part["part_id"])
            if not candidate:
                continue
            requirements = "\n".join(f"- {r['label']}: {requirement_value(r)}" for r in part["requirements"])
            gaps = [e["note"] for e in candidate["evidence"] if e["status"] != "supported"]
            gaps.append("Provide a dated quotation, availability, delivery schedule and supporting material, inspection and conformity evidence; none is verified yet.")
            body = (f"Request for quotation — no purchase commitment\nProduct: {p['name']}\nPart: {part['name']}\nQuantity: {part['quantity']}\n\n"
                    f"Source specifications:\n{requirements}\n\nPlease quote price, currency, lead time and any exceptions. "
                    "Supply evidence for material, dimensions, inspection and any required certifications. This is an information request, not an order.\n")
            if candidate["data_origin"] == "synthetic_demo":
                body += "\nSIMULATED DEMO: supplier, quotation and mailbox delivery are fictional.\n"
            items.append({"part_id": part["part_id"], "part_name": part["name"], "quantity": part["quantity"], "supplier_name": candidate["supplier_name"],
                          "candidate_id": candidate["candidate_id"], "data_origin": candidate["data_origin"], "requirements": copy.deepcopy(part["requirements"]),
                          "evidence_gaps": gaps, "rfq_text": body})
        return {"package_id": "agent-rfq-" + _business_id(agent["run_id"], str(p["input_version"])), "status": "draft", "input_version": p["input_version"],
                "items": items, "created_at": st.now_iso(), "approval_scope": "simulation_only",
                "notice": "Agent-prepared nonbinding RFQs. Demo mailbox activity is simulated. No order or payment is authorized."}

    def _simulate_agent_mailbox(self, p: dict, candidates: dict) -> None:
        """Only an in-app, persisted simulation; no provider/network/SMTP call exists."""
        agent = p["agent"]
        if agent["mode"] != "demo" or agent["mandate"]["outreach"] != "demo_mailbox" or agent["input_version"] != p["input_version"]:
            raise invalid("This mandate does not authorize demo mailbox delivery.")
        existing = {m["message_id"] for m in p.setdefault("mailbox", [])}
        for item in p["package"]["items"]:
            candidate = candidates[item["part_id"]]
            if candidate["data_origin"] != "synthetic_demo":
                raise invalid("Real supplier results cannot be delivered through the fictional demo mailbox.")
            key = _business_id(p["project_id"], agent["run_id"], str(p["input_version"]), p["package"]["package_id"], candidate["candidate_id"])
            outbound, inbound = f"mail-out-{key}", f"mail-in-{key}"
            base = {"run_id": agent["run_id"], "part_id": item["part_id"], "candidate_id": candidate["candidate_id"], "delivery": "simulated",
                    "data_origin": "synthetic_demo", "intended_supplier": candidate["supplier_name"], "created_at": st.now_iso()}
            if outbound not in existing:
                p["mailbox"].append({**base, "message_id": outbound, "direction": "outbound", "from_label": "Re::Source demo buyer mailbox",
                                      "to_label": "Simulated supplier inbox", "subject": f"Demo RFQ: {item['part_name']}", "body": item["rfq_text"]})
                self._event(p, "agent.mail_simulated", f"Simulated quote request for {candidate['supplier_name']} delivered to the in-app demo mailbox.", item["part_id"])
            if inbound not in existing:
                quote = {key: candidate.get(key) for key in ("price", "currency", "lead_time_days")}
                price = f"{quote['price']:g} {quote['currency'] or '(currency not supplied)'}" if quote["price"] is not None else "not supplied"
                lead = f"{quote['lead_time_days']} days" if quote["lead_time_days"] is not None else "not supplied"
                body = (f"SIMULATED SUPPLIER REPLY — fictional demonstration data.\nPart: {item['part_name']}\nSample unit price: {price}\n"
                        f"Sample lead time: {lead}\n\nMaterial, inspection and certification evidence has not been supplied. "
                        "All compliance requirements remain unverified. This reply is not a real commercial offer.")
                p["mailbox"].append({**base, "message_id": inbound, "direction": "inbound", "from_label": "Simulated supplier mailbox",
                                      "to_label": "Re::Source demo buyer inbox", "subject": f"Re: Demo RFQ: {item['part_name']}", "body": body,
                                      "quote": quote, "in_reply_to": outbound})
                self._event(p, "agent.reply_simulated", f"Received a labelled sample quote for {item['part_name']}; compliance evidence is still missing.", item["part_id"])
        agent["sent_count"] = sum(m["run_id"] == agent["run_id"] and m["direction"] == "outbound" for m in p["mailbox"])
        agent["reply_count"] = sum(m["run_id"] == agent["run_id"] and m["direction"] == "inbound" for m in p["mailbox"])
