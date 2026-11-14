"""DocumentExtractor (PRD FR-04): typed facts with locators and confidence.

Backends, chosen by RS_EXTRACTION_BACKEND (auto = databricks → openai → structured parse):
  * databricks: `ai_extract` on the SQL warehouse (Databricks Document AI)
  * openai:     structured-output extraction with the app's model
  * structured: deterministic parser for the structured FIELD: value body
Generative output is always cross-checked against the deterministic structured parse and validated in
code (types, identifiers, dates, site identity). Identical content is deduplicated by content hash.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from ..config import settings
from ..domain.extraction import FIELD_SCHEMAS, coerce, normalise_for_compare, parse_structured_form
from .databricks_sql import databricks_sql
from .model_client import model_client
from .store import OperationalStore

log = logging.getLogger("recovery.extractor")


class DocumentExtractor:
    def __init__(self, store: OperationalStore):
        self.store = store
        self.last_mode: str = "none"
        self.last_error: str | None = None
        self._databricks_disabled_until = 0.0

    def _backend(self) -> str:
        b = settings.extraction_backend
        if b != "auto":
            return b
        if databricks_sql.configured and time.time() > self._databricks_disabled_until:
            return "databricks"
        if model_client.available:
            return "openai"
        return "structured"

    def extract(self, evidence: list[dict]) -> dict[str, Any]:
        """Returns {"facts": {version_id: {field: fact}}, "modes": {version_id: mode}, "cached": [...], "backend": str}."""
        facts: dict[str, dict] = {}
        modes: dict[str, str] = {}
        cached: list[str] = []
        todo: list[dict] = []
        for ev in evidence:
            hit = self.store.cached_facts(ev["hash"], ev["doc_type"])
            if hit:
                facts[ev["version_id"]] = self._rebind(hit["facts"], ev)
                modes[ev["version_id"]] = hit["mode"]
                cached.append(ev["version_id"])
            else:
                todo.append(ev)
        backend = self._backend()
        generated: dict[str, dict] = {}
        if todo and backend == "databricks":
            try:
                generated = databricks_sql.ai_extract_batch(
                    [(ev["version_id"], ev["content_text"], list(FIELD_SCHEMAS[ev["doc_type"]].keys())) for ev in todo])
                mode = "databricks_ai_extract"
            except Exception as exc:  # noqa: BLE001
                self.last_error = f"ai_extract failed: {str(exc)[:200]}"
                log.warning(self.last_error)
                self._databricks_disabled_until = time.time() + 300
                backend = "openai" if model_client.available else "structured"
        if todo and backend == "openai":
            for ev in todo:
                out = model_client.extract(ev["doc_type"], ev["content_text"], {k: k for k in FIELD_SCHEMAS[ev["doc_type"]]})
                if out:
                    generated[ev["version_id"]] = out
            mode = "openai_structured_output"
        if todo and backend == "structured":
            mode = "structured_parse"
        for ev in todo:
            built = self._build_facts(ev, generated.get(ev["version_id"]), mode if ev["version_id"] in generated else "structured_parse")
            facts[ev["version_id"]] = built
            modes[ev["version_id"]] = next(iter(built.values()))["extraction_mode"] if built else "structured_parse"
            self.store.cache_facts(ev["hash"], ev["doc_type"], modes[ev["version_id"]], built)
        self.last_mode = backend
        return {"facts": facts, "modes": modes, "cached": cached, "backend": backend}

    @staticmethod
    def _rebind(cached: dict, ev: dict) -> dict:
        out = {}
        for fld, f in cached.items():
            f = dict(f)
            f["evidence_version_id"] = ev["version_id"]
            f["fact_id"] = f"fact:{ev['version_id']}:{fld}"
            out[fld] = f
        return out

    def _build_facts(self, ev: dict, generated: dict | None, mode: str) -> dict[str, dict]:
        schema = FIELD_SCHEMAS[ev["doc_type"]]
        parsed = parse_structured_form(ev["content_text"] or "")
        out: dict[str, dict] = {}
        for fld, type_code in schema.items():
            det = parsed.get(fld)
            gen_raw = (generated or {}).get(fld) if generated else None
            det_val, det_state, det_note = coerce(type_code, det[0]) if det else (None, "invalid", "absent")
            gen_val, gen_state, gen_note = coerce(type_code, gen_raw) if gen_raw not in (None, "") else (None, "invalid", "absent")
            note = None
            if generated is not None and gen_state == "valid" and det_state == "valid":
                agree = normalise_for_compare(gen_val) == normalise_for_compare(det_val)
                value, state = det_val, "valid"
                confidence = 0.98 if agree else 0.6
                fmode = f"{mode}+structured_parse_{'agree' if agree else 'disagree'}"
                if not agree:
                    note = f"Generative extraction returned '{gen_raw}', structured field reads '{det[0]}'; structured field kept (higher authority)."
            elif det_state == "valid":
                value, state, confidence = det_val, "valid", 0.9
                fmode = "structured_parse" if generated is None else f"{mode}_missing+structured_parse"
                note = det_note
            elif generated is not None and gen_state == "valid":
                value, state, confidence = gen_val, "valid", 0.7
                fmode = mode
                note = "Only generative extraction found this value."
            else:
                value, state, confidence, fmode = None, "invalid", None, mode if generated is not None else "structured_parse"
                note = det_note or gen_note
            if det is None and value is None and fld not in parsed:
                continue  # field genuinely absent from this document
            out[fld] = {
                "fact_id": f"fact:{ev['version_id']}:{fld}",
                "evidence_version_id": ev["version_id"],
                "field": fld,
                "typed_value": value,
                "unit": "days" if fld.endswith("_days") else ("GBP" if fld == "unit_price" and False else None),
                "original_value": det[0] if det else (str(gen_raw) if gen_raw is not None else None),
                "locator": {"line": det[1], "excerpt": f"{fld.upper().replace('_', ' ')}: {det[0]}"[:200]} if det else None,
                "confidence": confidence,
                "validation_state": state,
                "validation_note": note,
                "extraction_mode": fmode,
            }
        return out
