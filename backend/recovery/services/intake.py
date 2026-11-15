"""Intake & mesh service (contract v1.1).

* Uploads: content-addressed (sha256) blobs with an allowlist, size cap and magic-byte checks.
* Part requirements: extraction with per-field source references (Databricks ai_parse_document +
  ai_extract, OpenAI structured output, or the deterministic `KEY: value` parse), code validation,
  versioned human review, and confirmation through the normal change gateway so affected cases reassess.
* Mesh jobs: validate an uploaded segmented GLB against the expected component nodes and activate it as a
  new engine manifest version with provenance. Blueprint → mesh generation needs a real provider; without
  one the job reports `provider_required` and nothing is generated (never a fake success).
"""

from __future__ import annotations

import copy
from contextvars import copy_context
import io
import json
import logging
import math
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from ..adapters.blob_store import blob_store
from ..adapters.databricks_sql import databricks_sql
from ..adapters.glb import GLTFError, aggregate, is_glb, load_json, parse_nodes
from ..adapters.model_client import model_client
from ..config import settings
from ..domain.errors import DomainError, conflict, invalid, not_found
from ..domain.extraction import coerce, field_key, normalise_for_compare, parse_structured_form

log = logging.getLogger("recovery.intake")

MAX_UPLOAD_BYTES = (4 if settings.serverless else 50) * 1024 * 1024
MEDIA_TYPES = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".txt": "text/plain",
               ".md": "text/markdown", ".json": "application/json", ".glb": "model/gltf-binary", ".gltf": "model/gltf+json"}
ALLOWED_BY_KIND = {
    "blueprint": {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".md", ".json"},
    "part_requirements": {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".md", ".json"},
    "mesh_glb": {".glb", ".gltf"},
}
TEXT_EXTS = {".txt", ".md", ".json"}

# name, label, type code (domain/extraction.coerce), required, synonyms for the structured parse
REQUIREMENT_FIELDS: list[tuple[str, str, str, bool, tuple[str, ...]]] = [
    ("part_number", "Part number", "partno", True, ("part_no", "pn", "part")),
    ("revision", "Revision", "revision", True, ("rev", "part_revision")),
    ("description", "Description", "str", False, ("part_description", "name")),
    ("material", "Material", "str", False, ("materials", "alloy")),
    ("mating_interfaces", "Mating interfaces", "str", False, ("interfaces", "interface")),
    ("key_dimensions", "Key dimensions", "str", False, ("dimensions", "critical_dimensions")),
    ("tolerances", "Tolerances", "str", False, ("tolerance", "dimensional_tolerances")),
    ("certifications", "Certifications", "list", False, ("certificates", "required_certifications")),
    ("drawing_units", "Drawing units", "str", False, ("units", "measurement_units")),
    ("applicable_standards", "Applicable standards", "list", False, ("standards", "specifications")),
    ("inspection_requirements", "Inspection requirements", "str", False, ("inspection", "inspections")),
    ("effectivity", "Effectivity", "list", False, ("engine_effectivity", "applicability")),
]
LABELS = [f[0] for f in REQUIREMENT_FIELDS]


def _dimensional_unit(value: Any) -> Optional[str]:
    """Return an explicit, unambiguous length unit; leave mixed or absent units unknown."""
    if not isinstance(value, str):
        return None
    found = re.findall(r"(?<![\w.])[+-]?\d+(?:\.\d+)?\s*(mm|cm|m|inches|inch|in|um|µm|μm)\b", value, re.IGNORECASE)
    normalised = {"in" if unit.lower() in {"in", "inch", "inches"} else "um" if unit.lower() in {"um", "µm", "μm"}
                  else unit.lower() for unit in found}
    return next(iter(normalised)) if len(normalised) == 1 else None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ext(filename: str) -> str:
    name = (filename or "").lower().strip()
    return ("." + name.rsplit(".", 1)[1]) if "." in name else ""


def _check_magic(ext: str, data: bytes) -> Optional[str]:
    if ext == ".pdf" and not data.startswith(b"%PDF"):
        return "file does not start with %PDF"
    if ext == ".png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "file is not a PNG"
    if ext in (".jpg", ".jpeg") and not data.startswith(b"\xff\xd8"):
        return "file is not a JPEG"
    if ext == ".glb" and not is_glb(data):
        return "file is not a binary glTF (GLB)"
    if ext in TEXT_EXTS | {".gltf"}:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return "text file is not UTF-8"
        if ext in (".json", ".gltf"):
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                return f"invalid JSON: {exc}"
    return None


class IntakeService:
    def __init__(self, services: Any):
        self.s = services
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ helpers
    def _run_id(self) -> str:
        return self.s.scenario.ensure_run()["scenario_run_id"]

    def _emit(self, type_: str, summary: str, data: dict) -> None:
        try:
            self.s.bus.publish(self._run_id(), "__run__", type_, summary, data, data_origin="provided_document")
        except Exception:  # noqa: BLE001 - events never block intake
            log.exception("intake event failed")

    def _scope_key(self, key: str) -> str:
        # Uploads, extraction drafts and active manifests belong to this run.
        return f"run:{self._run_id()}:{key}"

    def _kv(self, key: str) -> Optional[dict]:
        return self.s.store.kv_get(self._scope_key(key))

    def _put(self, key: str, value: Any) -> None:
        self.s.store.kv_set(self._scope_key(key), value)

    # ------------------------------------------------------------------ uploads
    def upload(self, data: bytes, filename: str, kind: str, engine_id: str = "engine-demo-001", component_id: Optional[str] = None) -> dict:
        if kind not in ALLOWED_BY_KIND:
            raise invalid(f"kind must be one of {sorted(ALLOWED_BY_KIND)}")
        if engine_id != self.s.catalog.engine["engine_id"]:
            raise not_found(f"engine {engine_id}")
        if component_id and component_id not in self.s.catalog.components:
            raise invalid(f"unknown component_id {component_id}")
        if not data:
            raise invalid("empty file")
        if len(data) > MAX_UPLOAD_BYTES:
            raise DomainError(413, "PAYLOAD_TOO_LARGE", f"upload exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
        ext = _ext(filename)
        if ext not in ALLOWED_BY_KIND[kind]:
            raise invalid(f"extension {ext or '(none)'} not allowed for kind {kind}", allowed=sorted(ALLOWED_BY_KIND[kind]))
        problem = _check_magic(ext, data)
        if problem:
            raise invalid(f"file content rejected: {problem}")
        sha, path = blob_store.put_local(data, ext)
        dedup_key = f"intake:sha:{kind}:{component_id or '-'}:{sha}"
        existing_id = self._kv(dedup_key)
        if existing_id:
            existing = self._kv(f"intake:upload:{existing_id}")
            if existing:
                return {**existing, "duplicate_of": existing_id}
        if settings.serverless:
            # Never acknowledge an upload that exists only on an ephemeral worker disk.
            vpath = blob_store.mirror(sha, ext)
            if not vpath:
                raise DomainError(503, "UPLOAD_STORAGE_UNAVAILABLE", "Durable document storage is unavailable; retry later.")
        upload_id = f"upl-{uuid.uuid4().hex[:12]}"
        rec = {"upload_id": upload_id, "sha256": sha, "kind": kind, "filename": os.path.basename(filename)[:200], "media_type": MEDIA_TYPES[ext],
               "size_bytes": len(data), "engine_id": engine_id, "component_id": component_id, "storage_uri": f"local://uploads/{sha}{ext}",
               "mirrors": [], "status": "received", "duplicate_of": None, "created_at": _now(), "data_origin": "provided_document", "ext": ext}
        if settings.serverless:
            rec.update(storage_uri=vpath, status="mirrored")
        self._put(f"intake:upload:{upload_id}", rec)
        self._put(dedup_key, upload_id)
        self._emit("intake.uploaded", f"Upload received: {rec['filename']} ({kind}, {len(data):,} bytes)",
                   {"upload_id": upload_id, "kind": kind, "sha256": sha, "component_id": component_id})
        if databricks_sql.configured and not settings.serverless:
            from ..runtime.context import job_run_id
            ctx = copy_context()
            ctx.run(job_run_id.set, self._run_id())
            threading.Thread(target=ctx.run, args=(self._mirror, upload_id), daemon=True, name=f"mirror-{upload_id}").start()
        return self.public_upload(rec)

    def _mirror(self, upload_id: str) -> Optional[str]:
        rec = self._kv(f"intake:upload:{upload_id}")
        if not rec:
            return None
        if rec.get("status") == "mirrored":
            return rec["storage_uri"]
        vpath = blob_store.mirror(rec["sha256"], rec["ext"])
        rec = self._kv(f"intake:upload:{upload_id}") or rec
        if vpath:
            rec.update(storage_uri=vpath, status="mirrored", mirrors=sorted(set(rec.get("mirrors", [])) | {f"local://uploads/{rec['sha256']}{rec['ext']}"}))
        else:
            rec.update(status="mirror_failed", mirror_error=blob_store.last_error)
        self._put(f"intake:upload:{upload_id}", rec)
        return vpath

    @staticmethod
    def public_upload(rec: dict) -> dict:
        return {k: v for k, v in rec.items() if k not in ("ext", "mirror_error")}

    def get_upload(self, upload_id: str) -> dict:
        rec = self._kv(f"intake:upload:{upload_id}")
        if not rec:
            raise not_found(f"upload {upload_id}")
        return rec

    def content(self, upload_id: str) -> tuple[bytes, str, str]:
        rec = self.get_upload(upload_id)
        vol = rec["storage_uri"] if rec.get("status") == "mirrored" else None
        try:
            data = blob_store.read(rec["sha256"], rec["ext"], vol)
        except FileNotFoundError as exc:
            raise not_found(f"content for upload {upload_id}") from exc
        return data, rec["media_type"], rec["filename"]

    # ------------------------------------------------------------------ part requirements
    def start_part_requirements(self, upload_id: str, component_id: str) -> dict:
        rec = self.get_upload(upload_id)
        if rec["kind"] not in ("part_requirements", "blueprint"):
            raise invalid(f"upload {upload_id} is a {rec['kind']}, not a part-requirements document or blueprint")
        if component_id not in self.s.catalog.components:
            raise invalid(f"unknown component_id {component_id}")
        if rec.get("component_id") and rec["component_id"] != component_id:
            raise invalid("upload is associated with a different component")
        draft_id = f"preq-{uuid.uuid4().hex[:12]}"
        now = _now()
        draft = {"draft_id": draft_id, "upload_id": upload_id, "component_id": component_id, "scenario_run_id": self._run_id(), "version": 1,
                 "status": "extracting", "fields": [], "extraction": {"started_at": now}, "history": [], "change_id": None,
                 "affected_case_ids": [], "confirmed_by": None, "confirmed_at": None, "overlay": None, "created_at": now, "updated_at": now}
        self._put(f"intake:draft:{draft_id}", draft)
        if settings.job_backend == "vercel":
            self.s.jobs.enqueue("extract", self._run_id(), {"draft_id": draft_id}, key=draft_id)
            return draft
        from ..runtime.context import job_run_id
        ctx = copy_context()
        ctx.run(job_run_id.set, self._run_id())
        t = threading.Thread(target=ctx.run, args=(self._extract_safe, draft_id), daemon=True, name=f"extract-{draft_id}")
        with self._lock:
            self._threads[draft_id] = t
        t.start()
        return draft

    def _extract_safe(self, draft_id: str) -> None:
        try:
            self._extract(draft_id)
        except Exception as exc:  # noqa: BLE001
            log.exception("part requirement extraction failed")
            d = self._kv(f"intake:draft:{draft_id}")
            if d:
                d.update(status="failed", updated_at=_now())
                d["extraction"].update(error=str(exc)[:500], finished_at=_now())
                self._put(f"intake:draft:{draft_id}", d)
        finally:
            with self._lock:
                self._threads.pop(draft_id, None)

    def _document_text(self, rec: dict) -> tuple[str, list[dict], str, Optional[str]]:
        """Return (text, elements[{text, page, bbox, line, element_id}], mode, note)."""
        ext = rec["ext"]
        data, _, _ = self.content(rec["upload_id"])
        if ext in TEXT_EXTS:
            text = data.decode("utf-8")
            return text, [{"text": ln, "page": 1, "bbox": None, "line": i, "element_id": None} for i, ln in enumerate(text.splitlines(), 1)], "text", None
        backend = settings.extraction_backend
        if databricks_sql.configured and backend in ("auto", "databricks"):
            vpath = self._mirror(rec["upload_id"])
            if vpath and blob_store.is_safe_volume_path(vpath):
                try:
                    rows = databricks_sql.query(  # path is a validated content-addressed volume path (no user text)
                        f"SELECT CAST(ai_parse_document(content) AS STRING) AS p FROM read_files('{vpath}', format => 'binaryFile')")
                    elements = self._parse_ai_document(rows[0]["p"] if rows else "")
                    if elements:
                        return "\n".join(e["text"] for e in elements), elements, "databricks_ai_parse_document", None
                    note = "ai_parse_document returned no text elements"
                except Exception as exc:  # noqa: BLE001
                    note = f"ai_parse_document failed: {str(exc)[:200]}"
            else:
                note = f"volume mirror unavailable ({blob_store.last_error or 'not configured'})"
        else:
            note = "Databricks document parsing not available in this environment"
        if ext == ".pdf":
            try:
                from pypdf import PdfReader  # optional; not a declared dependency
                import io

                reader = PdfReader(io.BytesIO(data))
                elements, line_no = [], 0
                for p_i, page in enumerate(reader.pages, 1):
                    for ln in (page.extract_text() or "").splitlines():
                        line_no += 1
                        elements.append({"text": ln, "page": p_i, "bbox": None, "line": line_no, "element_id": None})
                if elements:
                    return "\n".join(e["text"] for e in elements), elements, "pypdf_text", note
            except ImportError:
                pass
        return "", [], "unavailable", note

    @staticmethod
    def _parse_ai_document(raw: str) -> list[dict]:
        if not raw:
            return []
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            return []
        doc = d.get("document", d) if isinstance(d, dict) else {}
        els = doc.get("elements") or [e for p in doc.get("pages", []) for e in (p.get("elements") or [])]
        out, line = [], 0
        for i, el in enumerate(els):
            content = (el.get("content") or el.get("text") or "").strip()
            if not content:
                continue
            bb = el.get("bbox") or []
            first = bb[0] if isinstance(bb, list) and bb and isinstance(bb[0], dict) else {}
            page = first.get("page_id", el.get("page_id"))
            coord = first.get("coord")
            for ln in content.splitlines():
                line += 1
                out.append({"text": ln, "page": (int(page) + 1) if isinstance(page, int) else None, "bbox": coord, "line": line,
                            "element_id": str(el.get("id", i))})
        return out

    def _structured(self, text: str) -> dict[str, tuple[str, int]]:
        parsed = parse_structured_form(text)
        out: dict[str, tuple[str, int]] = {}
        for name, _, _, _, syn in REQUIREMENT_FIELDS:
            for key in (name, *syn):
                if field_key(key) in parsed:
                    out[name] = parsed[field_key(key)]
                    break
        return out

    @staticmethod
    def _component_section(text: str, elements: list[dict], component_id: str) -> tuple[str, list[dict], Optional[str]]:
        """Select explicit COMPONENT_ID sections; never mix repeated part identities."""
        markers = []
        part_numbers = set()
        for index, element in enumerate(elements):
            line = element.get("text", "")
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key, value = field_key(key), value.strip()
            if key == "component_id":
                markers.append((index, value))
            elif key in {"part_number", "part_no", "pn", "part"} and value:
                part_numbers.add(value.upper())
        if markers:
            matching = [i for i, (_, value) in enumerate(markers) if value == component_id]
            if len(matching) != 1:
                return "", [], "No unique COMPONENT_ID section matches this component; fields require manual review"
            section_index = matching[0]
            start = markers[section_index][0] + 1
            end = markers[section_index + 1][0] if section_index + 1 < len(markers) else len(elements)
            scoped = elements[start:end]
            section_parts = set()
            for element in scoped:
                line = element.get("text", "")
                if ":" in line:
                    key, value = line.split(":", 1)
                    if field_key(key) in {"part_number", "part_no", "pn", "part"} and value.strip():
                        section_parts.add(value.strip().upper())
            if len(section_parts) > 1:
                return "", [], "Multiple part numbers occur in this component section; fields require manual review"
            return "\n".join(e["text"] for e in scoped), scoped, None
        if len(part_numbers) > 1:
            return "", [], "Multiple part numbers lack COMPONENT_ID sections; fields require manual review"
        return text, elements, None

    @staticmethod
    def _locate(value: Any, elements: list[dict], line: Optional[int] = None) -> Optional[dict]:
        el = None
        if line is not None:
            el = next((e for e in elements if e["line"] == line), None)
        if el is None and value not in (None, "", []):
            needle = str(value[0] if isinstance(value, list) else value).strip().lower()
            if len(needle) >= 2:
                pattern = re.compile(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", re.IGNORECASE)
                el = next((e for e in elements if pattern.search(e["text"])), None)
        if el is None:
            return None
        return {"page": el["page"], "bbox": el["bbox"], "excerpt": el["text"][:200], "line": el["line"], "element_id": el["element_id"]}

    def _extract(self, draft_id: str) -> None:
        draft = self._kv(f"intake:draft:{draft_id}")
        rec = self.get_upload(draft["upload_id"])
        text, elements, text_mode, note = self._document_text(rec)
        text, elements, scope_note = self._component_section(text, elements, draft["component_id"])
        if scope_note:
            note = f"{note}; {scope_note}" if note else scope_note
        generated: Optional[dict] = None
        gen_mode = None
        backend = settings.extraction_backend
        if text and backend in ("auto", "databricks") and databricks_sql.configured:
            try:
                generated = databricks_sql.ai_extract_batch([(draft_id, text[:20000], LABELS)]).get(draft_id)
                gen_mode = "databricks_ai_extract"
            except Exception as exc:  # noqa: BLE001
                note = (note + "; " if note else "") + f"ai_extract failed: {str(exc)[:160]}"
        if generated is None and text and backend in ("auto", "openai") and model_client.available:
            generated = model_client.extract("part_requirements", text[:20000], {n: lbl for n, lbl, *_ in REQUIREMENT_FIELDS})
            gen_mode = "openai_structured_output" if generated else None
        structured = self._structured(text) if text else {}
        # Structured-parser line numbers refer to the scoped text; preserve original source locators.
        structured = {name: (value, elements[line - 1]["line"]) for name, (value, line) in structured.items()}
        fields = []
        for name, label, type_code, required, _ in REQUIREMENT_FIELDS:
            det = structured.get(name)
            gen_raw = (generated or {}).get(name)
            det_val, det_state, det_note = coerce(type_code, det[0]) if det else (None, "absent", None)
            gen_val, gen_state, gen_note = coerce(type_code, gen_raw) if gen_raw not in (None, "") else (None, "absent", None)
            vnote = None
            if det_state == "valid" and gen_state == "valid":
                agree = normalise_for_compare(det_val) == normalise_for_compare(gen_val)
                value, state, conf = det_val, "valid", 0.95 if agree else 0.6
                mode = f"{gen_mode}+structured_parse_{'agree' if agree else 'disagree'}"
                if not agree:
                    vnote = f"Generative extraction read '{gen_raw}'; structured field '{det[0]}' kept."
            elif det_state == "valid":
                value, state, conf, mode = det_val, "valid", 0.85, "structured_parse"
            elif gen_state == "valid":
                value, state, conf, mode = gen_val, "valid", 0.7, gen_mode
            elif det_state == "invalid" or gen_state == "invalid":
                value, state, conf, mode = (det[0] if det else gen_raw), "invalid", None, "structured_parse" if det else gen_mode
                vnote = det_note or gen_note
            else:
                value, state, conf, mode = None, "unknown", None, None
                vnote = "not found in the document" if text else (note or "no text could be read from this file")
            from_structured = bool(det) and det_state == "valid" and value is det_val
            loc = self._locate(value, elements, det[1] if from_structured or (det and state == "invalid") else None)
            if state == "valid" and not from_structured:
                supported = loc is not None
                if supported and isinstance(value, list):
                    source = next(e["text"] for e in elements if e["line"] == loc["line"])
                    supported = all(str(item).strip().lower() in source.lower() for item in value)
                if name == "part_number" and supported:
                    # A drawing/sheet identifier is not evidence of an OEM part number.
                    source = next(e["text"] for e in elements if e["line"] == loc["line"])
                    supported = bool(re.search(r"\b(?:part\s*(?:number|no\.?|#)|p\s*/\s*n|pn)\b", source, re.IGNORECASE))
                if not supported:
                    vnote = ("An OEM part number is not explicitly identified in the source; review is required."
                             if name == "part_number" else "AI suggestion has no complete supporting source passage; review is required.")
                    value, state, conf, loc = None, "unknown", None, None
            unit = _dimensional_unit(value) if name in ("key_dimensions", "tolerances") and state == "valid" else None
            fields.append({"name": name, "label": label, "value": value, "unit": unit, "required": required,
                           "source_ref": {"upload_id": rec["upload_id"], **loc} if loc else None, "confidence": conf,
                           "validation_state": state, "validation_note": vnote, "extraction_mode": mode, "edited_by": None, "edited_at": None})
        with self.s.store.tx():
            draft = self._kv(f"intake:draft:{draft_id}")
            draft.update(fields=fields, status="needs_review", updated_at=_now())
            draft["extraction"].update(finished_at=_now(), text_mode=text_mode, generative_mode=gen_mode, note=note,
                                       characters=len(text), elements=len(elements))
            self._put(f"intake:draft:{draft_id}", draft)
        valid = sum(1 for f in fields if f["validation_state"] == "valid")
        self._emit("intake.extracted", f"Part requirements extracted for {draft['component_id']}: {valid}/{len(fields)} fields valid",
                   {"draft_id": draft_id, "upload_id": rec["upload_id"], "component_id": draft["component_id"], "text_mode": text_mode,
                    "generative_mode": gen_mode, "valid_fields": valid})

    def get_draft(self, draft_id: str) -> dict:
        d = self._kv(f"intake:draft:{draft_id}")
        if not d:
            raise not_found(f"part-requirements draft {draft_id}")
        return d

    def patch_draft(self, draft_id: str, req: dict) -> dict:
        types = {n: t for n, _, t, _, _ in REQUIREMENT_FIELDS}
        confirm_payload = None
        command = {"expected_version": req["expected_version"], "field_edits": req.get("field_edits") or {},
                   "action": req.get("action"), "actor": req.get("actor", "demo-operator")}
        with self.s.store.tx() as c:
            run_id = self._run_id()
            self.s.store.lock_run(c, run_id)  # serialise draft edits (row lock on Postgres, BEGIN IMMEDIATE on SQLite)
            d = self.get_draft(draft_id)
            if d["status"] == "confirmed" and command["action"] == "confirm":
                replay = self._kv(f"intake:confirmation:{draft_id}") == command
                replay = replay or (not command["field_edits"] and command["expected_version"] == d["version"])
                if replay:
                    if not d.get("change_id") and d.get("overlay"):
                        # Recover drafts closed by an older build before the gateway completed.
                        res = self.s.changes.inject_requirement_change(d["scenario_run_id"], d["component_id"], d["overlay"], draft_id)
                        d.update(change_id=res["change"]["change_id"], affected_case_ids=res["affected_case_ids"], updated_at=_now())
                        self._put(f"intake:draft:{draft_id}", d)
                    return d
            if d["status"] in ("confirmed", "rejected"):
                raise conflict("DRAFT_CLOSED", f"draft is {d['status']}; upload a new document to change requirements")
            if d["status"] != "needs_review":
                raise conflict("DRAFT_NOT_READY", f"draft is {d['status']}")
            if req["expected_version"] != d["version"]:
                raise conflict("VERSION_MISMATCH", f"draft is at version {d['version']}", current_version=d["version"])
            edits = req.get("field_edits") or {}
            unknown = [k for k in edits if k not in types]
            if unknown:
                raise invalid(f"unknown fields {unknown}")
            if edits:
                d["history"].append({"version": d["version"], "fields": copy.deepcopy(d["fields"]), "at": _now()})
                for f in d["fields"]:
                    if f["name"] in edits:
                        raw = edits[f["name"]]
                        val, state, vnote = coerce(types[f["name"]], raw) if raw not in (None, "") else (None, "unknown", "cleared by reviewer")
                        unit = _dimensional_unit(val) if f["name"] in ("key_dimensions", "tolerances") and state == "valid" else None
                        f.update(value=val if state == "valid" else raw, unit=unit, source_ref=None,
                                 validation_state=state if state in ("valid", "invalid") else "unknown",
                                 validation_note=vnote, extraction_mode="user_edit", edited_by=req.get("actor", "demo-operator"), edited_at=_now(),
                                 confidence=1.0 if state == "valid" else None)
                d["version"] += 1
            action = req.get("action")
            if action == "reject":
                d["status"] = "rejected"
            elif action == "confirm":
                blocking = [f["name"] for f in d["fields"] if (f["required"] and f["validation_state"] != "valid") or f["validation_state"] == "invalid"]
                if blocking:
                    raise DomainError(422, "NOT_READY", "required fields are missing or invalid", details={"fields": blocking})
                vals = {f["name"]: f["value"] for f in d["fields"] if f["validation_state"] == "valid"}
                reviewed_by, reviewed_at = req.get("actor", "demo-operator"), _now()
                overlay = {"part_identity": {"part_number": vals["part_number"], "revision": vals["revision"]},
                           "documented": {k: v for k, v in vals.items() if k not in ("part_number", "revision")},
                           "reviewed_fields": copy.deepcopy(d["fields"]), "reviewed_by": reviewed_by, "reviewed_at": reviewed_at,
                           "draft_id": draft_id, "draft_version": d["version"], "upload_id": d["upload_id"],
                           "source_refs": {f["name"]: f["source_ref"] for f in d["fields"] if f["source_ref"]}}
                d.update(status="confirmed", confirmed_by=reviewed_by, confirmed_at=reviewed_at, overlay=overlay)
                confirm_payload = (d["scenario_run_id"], d["component_id"], overlay)
            d["updated_at"] = _now()
            self._put(f"intake:draft:{draft_id}", d)
            if confirm_payload:
                # The draft, overlay and invalidation commit together. Coordinator dispatch is
                # deferred by Store.after_commit, so no worker can read an uncommitted overlay.
                run_id, component_id, overlay = confirm_payload
                res = self.s.changes.inject_requirement_change(run_id, component_id, overlay, draft_id)
                d.update(change_id=res["change"]["change_id"], affected_case_ids=res["affected_case_ids"], updated_at=_now())
                self._put(f"intake:draft:{draft_id}", d)
                self._put(f"intake:confirmation:{draft_id}", command)
                self._emit("intake.confirmed", f"Part requirements confirmed for {component_id} → {len(res['affected_case_ids'])} case(s) reassessing",
                           {"draft_id": draft_id, "change_id": res["change"]["change_id"], "affected_case_ids": res["affected_case_ids"]})
        return d

    # ------------------------------------------------------------------ mesh jobs
    def engine_bounds(self) -> dict[str, list[float]]:
        mods = self.s.catalog.engine.get("asset", {}).get("modules", [])
        xs = [x for m in mods for x in m.get("x_range", [])] or [-2.0, 2.0]
        return {"x": [min(xs) - 0.5, max(xs) + 0.5], "y": [-1.5, 1.5], "z": [-1.5, 1.5]}

    def default_expected(self) -> list[dict]:
        return [{"component_id": c["component_id"], "node_name": c["mesh_mapping"]["node_name"], "source_ref": None}
                for c in self.s.catalog.manifest["components"]]

    def _mesh_source_ref(self, ref: Any, component_id: str) -> tuple[Optional[dict], list[str]]:
        """Resolve provenance in the current run; a nonempty citation is not proof of a source."""
        if not isinstance(ref, dict):
            return None, ["no source_ref back to the blueprint region"]
        ref = {k: ref[k] for k in ("upload_id", "page", "bbox", "excerpt", "line", "element_id", "note") if k in ref}
        upload_id = ref.get("upload_id")
        if not isinstance(upload_id, str) or not upload_id.strip():
            return ref, ["source_ref requires a document upload_id"]
        try:
            rec = self.get_upload(upload_id)
            data, _, _ = self.content(upload_id)
        except DomainError:
            return ref, ["source_ref upload or its content is not accessible in this run"]
        if rec["kind"] not in ("blueprint", "part_requirements"):
            return ref, ["source_ref must cite a blueprint or part-requirements document"]
        if rec["engine_id"] != self.s.catalog.engine["engine_id"] or rec.get("component_id") not in (None, component_id):
            return ref, ["source_ref document belongs to a different product or component"]
        problems = []
        for key in ("page", "line"):
            val = ref.get(key)
            if val is not None and (type(val) is not int or val < 1):
                problems.append(f"source_ref {key} must be a positive integer")
        for key in ("excerpt", "element_id", "note"):
            val = ref.get(key)
            if val is not None and (not isinstance(val, str) or not val.strip()):
                problems.append(f"source_ref {key} must be a nonempty string")
        bbox = ref.get("bbox")
        if bbox is not None:
            sane = (isinstance(bbox, list) and len(bbox) == 4
                    and all(type(v) in (int, float) and math.isfinite(v) for v in bbox))
            if not sane or not (0 <= bbox[0] < bbox[2] and 0 <= bbox[1] < bbox[3]):
                problems.append("source_ref bbox must contain finite, ordered page coordinates")
            if ref.get("page") is None:
                problems.append("source_ref bbox requires a page")
        if problems:
            return ref, problems
        page, line, excerpt = ref.get("page"), ref.get("line"), ref.get("excerpt")
        if rec["ext"] in TEXT_EXTS:
            lines = data.decode("utf-8").splitlines()
            if page not in (None, 1) or (line is not None and line > len(lines)):
                problems.append("source_ref page or line is outside the document")
            elif excerpt and excerpt.casefold() not in (lines[line - 1] if line else "\n".join(lines)).casefold():
                problems.append("source_ref excerpt is not present at the cited location")
            if not line and not excerpt:
                problems.append("text source_ref requires a line or a matching excerpt")
        else:
            if rec["ext"] in (".png", ".jpg", ".jpeg") and page != 1:
                problems.append("image source_ref page must be 1")
            if rec["ext"] == ".pdf":
                try:
                    from pypdf import PdfReader
                    page_count = len(PdfReader(io.BytesIO(data)).pages)
                except Exception:  # unreadable/encrypted files cannot establish a source page
                    problems.append("source_ref PDF page cannot be verified because the document is unreadable")
                else:
                    if page is not None and page > page_count:
                        problems.append("source_ref page is outside the PDF document")
            if not page or not (bbox or excerpt or ref.get("element_id")):
                problems.append("source_ref requires a page and a region, excerpt or element locator")
        return ref, problems

    def validate_glb(self, data: bytes, expected: list[dict], upload_id: Optional[str] = None) -> tuple[dict, dict]:
        bounds = self.engine_bounds()
        try:
            doc = load_json(data)
            nodes = parse_nodes(doc)
        except GLTFError as exc:
            return ({"ok": False, "checks": [], "engine_bounds": bounds, "node_count": 0, "mesh_count": 0, "problems": [str(exc)],
                     "validated_at": _now()}, {})
        by_name: dict[str, list[int]] = {}
        for n in nodes:
            if n.name:
                by_name.setdefault(n.name, []).append(n.index)
        checks, candidate = [], {}
        for exp in expected:
            idx = by_name.get(exp["node_name"], [])
            chk: dict[str, Any] = {"component_id": exp["component_id"], "node_name": exp["node_name"], "present": bool(idx), "unique": len(idx) == 1,
                                   "is_mesh": False, "vertex_count": 0, "bbox_min": None, "bbox_max": None, "centre": None,
                                   "non_degenerate_axes": 0, "inside_bounds": False, "has_source_ref": False, "source_ref": None, "problems": []}
            if not idx:
                chk["problems"].append("node not found")
            else:
                if len(idx) > 1:
                    chk["problems"].append(f"node name used {len(idx)} times")
                agg = aggregate(nodes, idx[0])
                chk.update(is_mesh=agg["is_mesh"], vertex_count=agg["vertex_count"], bbox_min=agg["bbox_min"], bbox_max=agg["bbox_max"])
                if not agg["is_mesh"]:
                    chk["problems"].append("node has no mesh geometry")
                if agg["vertex_count"] < 3:
                    chk["problems"].append(f"only {agg['vertex_count']} vertices")
                if agg["bbox_min"] and agg["bbox_max"]:
                    extent = [agg["bbox_max"][k] - agg["bbox_min"][k] for k in range(3)]
                    chk["non_degenerate_axes"] = sum(1 for e in extent if e > 1e-6)
                    centre = [round((agg["bbox_max"][k] + agg["bbox_min"][k]) / 2, 4) for k in range(3)]
                    chk["centre"] = centre
                    inside = (bounds["x"][0] <= centre[0] <= bounds["x"][1] and bounds["y"][0] <= centre[1] <= bounds["y"][1]
                              and bounds["z"][0] <= centre[2] <= bounds["z"][1])
                    chk["inside_bounds"] = inside
                    if chk["non_degenerate_axes"] < 2:
                        chk["problems"].append("degenerate geometry (flat on more than one axis)")
                    if not inside:
                        chk["problems"].append(f"centre {centre} outside engine bounds")
                else:
                    chk["problems"].append("POSITION accessor has no min/max bounds")
                ref = nodes[idx[0]].extras.get("source_ref")
                if ref is None:
                    ref = exp.get("source_ref")
                ref, source_problems = self._mesh_source_ref(ref, exp["component_id"])
                chk["source_ref"] = ref
                chk["has_source_ref"] = not source_problems
                chk["problems"].extend(source_problems)
            chk["ok"] = not chk["problems"]
            checks.append(chk)
            if chk["ok"]:
                c = chk["centre"]
                candidate[exp["component_id"]] = {"node_name": exp["node_name"], "bbox_min": chk["bbox_min"], "bbox_max": chk["bbox_max"],
                                                  "centre": c, "suggested_hotspot_anchor": [c[0], round(chk["bbox_max"][1], 4), c[2]],
                                                  "source_ref": chk["source_ref"]}
        expected_names = {e["node_name"] for e in expected}
        validation = {"ok": all(c["ok"] for c in checks) and bool(checks), "checks": checks, "engine_bounds": bounds, "node_count": len(nodes),
                      "mesh_count": sum(1 for n in nodes if n.mesh is not None), "problems": [], "validated_at": _now()}
        manifest_candidate = {"engine_id": self.s.catalog.engine["engine_id"], "upload_id": upload_id, "components": candidate,
                              "other_nodes": sorted(n for n in by_name if n not in expected_names)[:200]}
        return validation, manifest_candidate

    def create_mesh_job(self, req: dict) -> dict:
        rec = self.get_upload(req["upload_id"])
        if req.get("engine_id", "engine-demo-001") != self.s.catalog.engine["engine_id"]:
            raise not_found(f"engine {req.get('engine_id')}")
        expected = req.get("expected") or self.default_expected()
        known = set(self.s.catalog.components)
        bad = [e["component_id"] for e in expected if e["component_id"] not in known]
        if bad:
            raise invalid(f"unknown component_id(s) {bad}; component IDs are stable and cannot be invented by a mesh")
        job = {"job_id": f"mesh-{uuid.uuid4().hex[:12]}", "upload_id": rec["upload_id"], "engine_id": self.s.catalog.engine["engine_id"],
               "provider": None, "status": "queued", "message": "", "expected": expected, "validation": None, "manifest_candidate": None,
               "created_at": _now(), "activated_at": None, "manifest_version": None}
        if rec["kind"] == "mesh_glb":
            data, _, _ = self.content(rec["upload_id"])
            validation, candidate = self.validate_glb(data, expected, rec["upload_id"])
            ok = validation["ok"]
            failing = [f"{c['node_name']}: {', '.join(c['problems'])}" for c in validation["checks"] if not c["ok"]] + validation["problems"]
            job.update(provider="uploaded_glb", status="succeeded" if ok else "failed", validation=validation, manifest_candidate=candidate,
                       message=("All expected component nodes validated; activate to publish a new manifest version." if ok
                                else "Validation failed: " + "; ".join(failing)[:900]))
            self._emit("intake.validated", f"Mesh validation {'passed' if ok else 'failed'} for {rec['filename']}",
                       {"job_id": job["job_id"], "upload_id": rec["upload_id"], "ok": ok, "failing": failing[:10]})
        elif rec["kind"] == "blueprint":
            provider = os.getenv("RS_MESH_PROVIDER", "").strip()
            job.update(provider=provider or "none", status="provider_required",
                       message=(f"Mesh provider '{provider}' has no server-side adapter in this build; no mesh was generated." if provider else
                                "No server-side blueprint→mesh provider is configured (RS_MESH_PROVIDER unset); no mesh was generated. "
                                "Generate the segmented mesh with Blender/Unity or another generator, then upload it as kind=mesh_glb "
                                "for validation and activation."))
        else:
            raise invalid("mesh jobs take a mesh_glb or blueprint upload")
        self._put(f"intake:job:{job['job_id']}", job)
        return job

    def get_job(self, job_id: str) -> dict:
        j = self._kv(f"intake:job:{job_id}")
        if not j:
            raise not_found(f"mesh job {job_id}")
        return j

    def provenance(self) -> dict:
        ov = self._kv("manifest_override")
        if ov:
            return ov
        return {"manifest_version": self.s.catalog.manifest["manifest_version"], "kind": "procedural", "provider": None, "job_id": None,
                "upload_id": None, "glb_path": None, "activated_at": None, "source_refs": {}, "node_names": {}, "previous_manifest_version": None}

    def activate_job(self, job_id: str) -> dict:
        with self.s.store.tx() as c:
            self.s.store.lock_run(c, self._run_id())
            job = self.get_job(job_id)
            if job["status"] != "succeeded":
                raise conflict("MESH_JOB_NOT_ACTIVATABLE", f"mesh job is {job['status']}; only a validated (succeeded) job can be activated")
            data, _, _ = self.content(job["upload_id"])
            validation, candidate = self.validate_glb(data, job["expected"], job["upload_id"])
            if not validation["ok"]:
                raise conflict("MESH_SOURCE_INVALID", "Mesh geometry or source provenance is no longer valid; validate a new job",
                               validation=validation)
            job.update(validation=validation, manifest_candidate=candidate)
            if job.get("activated_at") and self.provenance().get("job_id") == job_id:
                return self.provenance()
            n = int(self._kv("manifest_override_counter") or 0) + 1
            prev = self.provenance()["manifest_version"]
            comps = job["manifest_candidate"]["components"]
            ov = {"manifest_version": f"{self.s.catalog.manifest['manifest_version']}+gen{n}", "kind": "generated", "provider": job["provider"],
                  "job_id": job_id, "upload_id": job["upload_id"], "glb_path": f"/api/v1/intake/uploads/{job['upload_id']}/content",
                  "activated_at": _now(), "source_refs": {cid: c.get("source_ref") for cid, c in comps.items()},
                  "node_names": {cid: c["node_name"] for cid, c in comps.items()},
                  "anchors": {cid: c["suggested_hotspot_anchor"] for cid, c in comps.items()}, "previous_manifest_version": prev}
            self._put("manifest_override_counter", n)
            self._put("manifest_override", ov)
            job.update(activated_at=ov["activated_at"], manifest_version=ov["manifest_version"])
            self._put(f"intake:job:{job_id}", job)
        self._emit("manifest.updated", f"Engine manifest {ov['manifest_version']} activated from validated mesh ({job['provider']})",
                   {"manifest_version": ov["manifest_version"], "job_id": job_id, "kind": "generated"})
        return ov

    def reset_manifest(self) -> dict:
        prev = self.provenance()
        if prev["kind"] == "procedural":
            return prev
        n = int(self._kv("manifest_override_counter") or 0) + 1
        ov = {"manifest_version": f"{self.s.catalog.manifest['manifest_version']}+reset{n}", "kind": "procedural", "provider": None,
              "job_id": None, "upload_id": None, "glb_path": None, "activated_at": _now(), "source_refs": {}, "node_names": {},
              "previous_manifest_version": prev["manifest_version"]}
        self._put("manifest_override_counter", n)
        self._put("manifest_override", ov)
        self._emit("manifest.updated", f"Engine manifest reset to procedural geometry ({ov['manifest_version']})",
                   {"manifest_version": ov["manifest_version"], "kind": "procedural"})
        return ov

    def apply_to_engine_view(self, engine: dict, components: list[dict]) -> tuple[dict, list[dict]]:
        prov = self.provenance()
        public = {k: v for k, v in prov.items() if k != "anchors"}
        engine = {**engine, "asset": {**engine.get("asset", {}), "provenance": public}, "scenario_manifest_version": prov["manifest_version"]}
        if prov["kind"] != "generated":
            return engine, components
        engine["asset"].update(kind="generated", glb_path=prov["glb_path"], provider=prov["provider"], job_id=prov["job_id"])
        out = []
        for comp in components:
            comp = copy.deepcopy(comp)
            cid = comp["component_id"]
            if cid in prov.get("node_names", {}):
                comp["mesh_mapping"]["node_name"] = prov["node_names"][cid]
                if prov.get("anchors", {}).get(cid):
                    comp["mesh_mapping"]["hotspot_anchor"] = prov["anchors"][cid]
            out.append(comp)
        return engine, out

    # ------------------------------------------------------------------ test helper
    def wait_idle(self, timeout: float = 30.0) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            with self._lock:
                threads = list(self._threads.values())
            if not threads:
                return True
            for t in threads:
                t.join(timeout=max(0.0, end - time.time()))
        return False
