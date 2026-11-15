"""Visitor-owned, durable product workspaces, separate from the engine scenario.

Only short state changes hold a database row lock. Provider calls happen outside
transactions; workers publish against an input revision so stale work cannot win.
"""
from __future__ import annotations

import copy
import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import copy_context
from pathlib import Path
from typing import Any

from sqlalchemy import select, text

from ..adapters import store as st
from ..adapters.blob_store import blob_store
from ..adapters.databricks_sql import databricks_sql
from ..adapters.external import linkup
from ..adapters.glb import GLTFError, load_json, parse_nodes
from ..config import settings
from ..domain.errors import DomainError, conflict, invalid, not_found
from ..domain.products import (
    DemoProduct,
    ProductModel,
    ProductPart,
    ProductProject,
    ProductProjectSummary,
)
from ..runtime.context import visitor_id
from .product_workers import ProductWorkers, literal_mention, requirement_value

log = logging.getLogger("recovery.products")


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


class ProductService(ProductWorkers):
    def __init__(self, services: Any):
        self.s = services
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="product")

    def capabilities(self) -> dict:
        return {
            "document_parsing": "databricks_configured" if databricks_sql.configured else "text_and_pdf_only",
            "requirement_extraction": "openai_configured" if self.s.model.available else "structured_documents_only",
            "supplier_discovery": "linkup_configured" if linkup.available else "sample_offers_only",
            "model_generation": "provider_required",
            "storage": "local_sqlite" if self.s.store.is_sqlite else "lakebase_postgres",
            "execution": "durable_queue" if settings.job_backend == "vercel" else "local_worker",
        }

    def _profiles(self) -> dict[str, dict]:
        profiles = {}
        for path in sorted((settings.data_dir / "demo-products").glob("*.json")):
            profile = json.loads(path.read_text())
            # Validate public fields at the boundary, including model provenance.
            ProductModel.model_validate(profile["model"])
            for part in profile["parts"]:
                ProductPart.model_validate(part)
            profiles[profile["demo_id"]] = profile
        return profiles

    def demos(self) -> list[dict]:
        return [DemoProduct.model_validate({**{k: p[k] for k in ("demo_id", "name", "description", "product_type", "model")},
                                            "part_count": len(p["parts"])}).model_dump(mode="json")
                for p in self._profiles().values()]

    @staticmethod
    def _owner() -> str:
        owner = visitor_id.get()
        if settings.public_demo and not owner:
            raise not_found("product")
        return owner or "__local__"

    def _load(self, project_id: str, *, lock: bool = False) -> dict:
        with self.s.store.tx() as conn:
            query = select(st.kv.c.value).where(st.kv.c.key == f"product:{project_id}")
            if lock:
                query = query.with_for_update()
            row = conn.execute(query).first()
            project = st.loads(row[0]) if row else None
            if not project or project["_owner"] != self._owner():
                raise not_found("product")
            return project

    @contextmanager
    def _mutate(self, project_id: str, expected_version: int | None = None):
        with self.s.store.tx():
            project = self._load(project_id, lock=True)
            if expected_version is not None and project["version"] != expected_version:
                raise conflict("PRODUCT_CHANGED", "This project changed. Refresh before saving your review.")
            before = copy.deepcopy(project)
            yield project
            if project == before:
                return
            project["version"] += 1
            project["updated_at"] = st.now_iso()
            self.s.store.kv_set(f"product:{project_id}", project)

    def _public(self, project: dict) -> dict:
        return ProductProject.model_validate({**{k: v for k, v in project.items() if not k.startswith("_")},
                                              "capabilities": self.capabilities()}).model_dump(mode="json")

    def get(self, project_id: str) -> dict:
        return self._public(self._load(project_id))

    def list_projects(self, limit: int = 100) -> dict:
        """Return the newest 1–100 owned summaries directly from durable storage.

        The database filters ownership before the limit and computes the counters,
        so document text, requirements and other visitors' records never leave the
        database for this dashboard read. No separate summary index can go stale.
        """
        if not 1 <= limit <= 100:
            raise invalid("The project summary limit must be between 1 and 100.")
        owner = self._owner()
        if self.s.store.is_sqlite:
            document = "value"
            owner_value = "json_extract(value, '$._owner')"
            field = lambda key: f"json_extract(document, '$.{key}')"
            array_count = lambda key: f"json_array_length({field(key)})"
            matching = lambda key, states: (f"(SELECT COUNT(*) FROM json_each(document, '$.{key}') AS item "
                                            f"WHERE json_extract(item.value, '$.status') IN ({states}))")
            selected_count = "(SELECT COUNT(*) FROM json_each(document, '$.selections'))"
            package_status = field("package.status")
        else:
            document = "CAST(value AS JSONB)"
            owner_value = f"{document} ->> '_owner'"
            field = lambda key: f"document ->> '{key}'"
            array_count = lambda key: f"jsonb_array_length(document -> '{key}')"
            matching = lambda key, states: (f"(SELECT COUNT(*) FROM jsonb_array_elements(document -> '{key}') AS item(value) "
                                            f"WHERE item.value ->> 'status' IN ({states}))")
            selected_count = "(SELECT COUNT(*) FROM jsonb_object_keys(document -> 'selections'))"
            package_status = "document -> 'package' ->> 'status'"
        columns = [f"{field(key)} AS {key}" for key in ("project_id", "name", "demo_id", "product_type", "status", "created_at", "updated_at")]
        columns += [f"{array_count('parts')} AS part_count", f"{matching('parts', "'confirmed'")} AS confirmed_part_count",
                    f"{array_count('research')} AS research_count", f"{matching('research', "'queued', 'running'")} AS active_research_count",
                    f"{matching('research', "'complete'")} AS completed_research_count", f"{matching('research', "'failed'")} AS failed_research_count",
                    f"{selected_count} AS selected_count", f"{package_status} AS package_status"]
        # Expressions and field names above are code constants. Only owner/limit
        # are request-dependent, and both remain bound SQL parameters.
        query = text(f"WITH owned AS (SELECT {document} AS document FROM kv WHERE key LIKE 'product:%' AND {owner_value} = :owner) "
                     f"SELECT {', '.join(columns)} FROM owned ORDER BY updated_at DESC, project_id DESC LIMIT :limit")
        with self.s.store.tx() as conn:
            rows = conn.execute(query, {"owner": owner, "limit": limit}).mappings().all()
        return {"projects": [ProductProjectSummary.model_validate(dict(row)).model_dump(mode="json") for row in rows]}

    @staticmethod
    def _event(project: dict, type_: str, summary: str, part_id: str | None = None) -> None:
        project["_event_sequence"] = project.get("_event_sequence", 0) + 1
        project["events"].append({"sequence": project["_event_sequence"], "type": type_, "summary": summary,
                                  "part_id": part_id, "created_at": st.now_iso()})
        project["events"] = project["events"][-500:]

    def create(self, demo_id: str | None = None, name: str | None = None) -> dict:
        profile = self._profiles().get(demo_id) if demo_id else None
        if demo_id and not profile:
            raise not_found("demo product")
        profile = copy.deepcopy(profile or {})
        pid, now = _id("product"), st.now_iso()
        parts = [ProductPart.model_validate(p).model_dump(mode="json") for p in profile.get("parts", [])]
        for part in parts:
            part["status"] = "proposed"
            for req in part["requirements"]:
                req["status"] = "proposed"
        project = {"project_id": pid, "name": name or profile.get("name", "Untitled product"), "demo_id": demo_id,
                   "product_type": profile.get("product_type", "custom"), "version": 1, "input_version": 1,
                   "status": "review" if parts else "draft", "documents": [], "parts": parts,
                   "model": ProductModel.model_validate(profile.get("model", {})).model_dump(mode="json"),
                   "research": [], "selections": {}, "package": None, "events": [], "created_at": now, "updated_at": now,
                   "_owner": self._owner(), "_documents": {}, "_event_sequence": 0, "_extract_job": None,
                   "_sample_offers": profile.get("sample_offers", [])}
        if profile:
            project["model"]["node_names"] = sorted({node for part in parts for node in part["node_names"]})
            self._mapping_status(project)
        for doc in profile.get("documents", []):
            text = doc["text"]
            project["_documents"][doc["document_id"]] = {**doc, "text": text, "media_type": "text/plain", "ext": ".txt"}
            project["documents"].append({"document_id": doc["document_id"], "name": doc["name"], "kind": doc["kind"],
                                          "data_origin": "synthetic_demo", "media_type": "text/plain", "size_bytes": len(text.encode()),
                                          "content_url": f"/api/v1/products/{pid}/documents/{doc['document_id']}/content",
                                          "extraction_status": "complete", "extraction_method": "prepared_demo", "excerpt": text[:900]})
        self._event(project, "project.created", "Demo project created with prepared geometry and sample specifications. Review the parts before research."
                    if demo_id else "Project created. Upload specifications or add parts to begin.")
        self.s.store.kv_set(f"product:{pid}", project)
        return self._public(project)

    @staticmethod
    def _invalidate(project: dict) -> None:
        project["input_version"] += 1
        project["research"] = []
        project["selections"] = {}
        project["package"] = None
        project["_extract_job"] = None

    @staticmethod
    def _mapping_status(project: dict) -> None:
        model = project["model"]
        available = set(model.get("node_names", []))
        mappings = [part["node_names"] for part in project["parts"]]
        valid = [nodes for nodes in mappings if nodes and set(nodes).issubset(available)]
        repeated = sum(len(nodes) for nodes in mappings) != len({node for nodes in mappings for node in nodes})
        model["mapping_status"] = "mapped" if valid and len(valid) == len(mappings) and not repeated else "partial" if valid else "unmapped"

    def upload(self, project_id: str, data: bytes, filename: str, kind: str) -> dict:
        from .intake import MAX_UPLOAD_BYTES, MEDIA_TYPES, _check_magic

        self._load(project_id)  # Check ownership before accepting any bytes into storage.
        allowed = {"blueprint": {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".md", ".json"},
                   "requirements": {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".md", ".json"}, "model": {".glb"}}
        ext = Path(filename).suffix.lower()
        if kind not in allowed or ext not in allowed[kind]:
            raise invalid("Unsupported document kind or file format.")
        if not data or len(data) > MAX_UPLOAD_BYTES:
            raise invalid(f"Upload must contain between 1 byte and {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
        if problem := _check_magic(ext, data):
            raise invalid(f"File content rejected: {problem}")
        nodes = []
        if kind == "model":
            try:
                doc = load_json(data)
                if any(item.get("uri") and not item["uri"].startswith("data:") for key in ("buffers", "images") for item in doc.get(key, [])):
                    raise invalid("Upload a self-contained GLB without external buffers or images.")
                nodes = [n.name for n in parse_nodes(doc) if n.name and n.mesh is not None]
                if not nodes:
                    raise invalid("The GLB needs named mesh nodes so parts can be selected.")
            except (GLTFError, ValueError, TypeError, KeyError) as exc:
                raise invalid("The uploaded model could not be read as a segmented GLB.") from exc
        sha, _ = blob_store.put_local(data, ext)
        volume_uri = blob_store.mirror(sha, ext) if settings.serverless or databricks_sql.configured else None
        if settings.serverless and not volume_uri:
            raise DomainError(503, "UPLOAD_STORAGE_UNAVAILABLE", "Durable upload storage is unavailable. Retry when Databricks storage is connected.", retryable=True)
        with self._mutate(project_id) as p:
            if any(d.get("sha256") == sha and d["kind"] == kind for d in p["_documents"].values()):
                return self._public(p)
            if len(p["documents"]) >= 12:
                raise invalid("A project supports up to twelve documents.")
            did = _id("doc")
            clean_name = Path(filename).name[:200]
            text = data.decode("utf-8") if ext in {".txt", ".md", ".json"} else ""
            p["_documents"][did] = {"document_id": did, "name": clean_name, "kind": kind, "sha256": sha, "ext": ext,
                                      "volume_uri": volume_uri, "media_type": MEDIA_TYPES[ext], "text": text, "node_names": nodes}
            p["documents"].append({"document_id": did, "name": clean_name, "kind": kind, "data_origin": "provided_document",
                                     "media_type": MEDIA_TYPES[ext], "size_bytes": len(data),
                                     "content_url": f"/api/v1/products/{project_id}/documents/{did}/content",
                                     "extraction_status": "complete" if text else "pending", "extraction_method": "text" if text else None,
                                     "excerpt": text[:900] or None})
            if kind != "model":
                self._invalidate(p)
                for part in p["parts"]:
                    part["status"] = "proposed"
                    for req in part["requirements"]:
                        req["status"] = "proposed"
                p["status"] = "review" if p["parts"] else "draft"
            self._event(p, "document.uploaded", f"Uploaded {clean_name}." )
        return self.get(project_id)

    def content(self, project_id: str, document_id: str) -> tuple[bytes, str, str]:
        doc = self._load(project_id)["_documents"].get(document_id)
        if not doc:
            raise not_found("document")
        if not doc.get("sha256"):
            return doc["text"].encode(), doc["media_type"], doc["name"]
        try:
            return blob_store.read(doc["sha256"], doc["ext"], doc.get("volume_uri")), doc["media_type"], doc["name"]
        except FileNotFoundError as exc:
            raise not_found("document content") from exc

    @staticmethod
    def _validate_sources(project: dict, parts: list[dict]) -> None:
        normalise = lambda value: " ".join(value.split()).casefold()
        for part in parts:
            for req in part["requirements"]:
                source = req.get("source")
                if source:
                    doc = project["_documents"].get(source["document_id"])
                    if not doc or doc["kind"] == "model" or normalise(source["quote"]) not in normalise(doc.get("text", "")):
                        raise invalid("A requirement citation must quote an uploaded or demo specification.")
                    if not literal_mention(requirement_value(req), source["quote"]):
                        raise invalid("A requirement value must appear in its source quote; clear the citation when entering a new value.")

    def review(self, project_id: str, parts: list[dict], confirm: bool, expected_version: int | None = None) -> dict:
        parts = [ProductPart.model_validate(part).model_dump(mode="json") for part in parts]
        if not parts or len({p["part_id"] for p in parts}) != len(parts):
            raise invalid("Part IDs must be unique and the project needs at least one part.")
        if any(len({r["key"] for r in p["requirements"]}) != len(p["requirements"]) for p in parts):
            raise invalid("Requirement keys must be unique within each part.")
        if confirm and any(not p["requirements"] for p in parts):
            raise invalid("Add at least one requirement for each part before confirmation.")
        with self._mutate(project_id, expected_version) as p:
            self._validate_sources(p, parts)
            for part in parts:
                part["status"] = "confirmed" if confirm else "proposed"
                for req in part["requirements"]:
                    req["status"] = part["status"]
            self._invalidate(p)
            p["parts"] = parts
            self._mapping_status(p)
            p["status"] = "ready" if confirm else "review"
            self._event(p, "requirements.confirmed" if confirm else "requirements.edited",
                        f"{'Confirmed' if confirm else 'Saved'} {len(parts)} parts and their requirements.")
        return self.get(project_id)

    def set_model(self, project_id: str, origin: str, document_id: str | None = None) -> dict:
        with self._mutate(project_id) as p:
            if origin == "generated":
                model = {"origin": "generated", "status": "provider_required", "notes": "Blueprint-to-3D generation needs a configured CAD/model provider. Upload a segmented GLB or use a prepared demo model."}
            elif origin == "prepared_demo":
                profile = self._profiles().get(p["demo_id"])
                if not profile:
                    raise invalid("This project has no prepared demo model.")
                model = profile["model"]
                model = {**model, "node_names": sorted({node for part in profile["parts"] for node in part["node_names"]})}
            elif origin == "uploaded":
                doc = p["_documents"].get(document_id)
                if not doc or doc["kind"] != "model":
                    raise invalid("Choose a GLB uploaded to this project.")
                nodes = doc["node_names"]
                mapped = [part for part in p["parts"] if part["node_names"] and set(part["node_names"]).issubset(nodes)]
                model = {"origin": "uploaded", "status": "ready", "asset_url": f"/api/v1/products/{project_id}/documents/{document_id}/content",
                         "document_id": document_id, "node_names": nodes,
                         "mapping_status": "mapped" if mapped and len(mapped) == len(p["parts"]) else "partial" if mapped else "unmapped",
                         "notes": "Uploaded geometry. Part-to-node mapping requires review; geometry does not establish engineering compliance."}
            else:
                raise invalid("Unknown model origin.")
            p["model"] = ProductModel.model_validate(model).model_dump(mode="json")
            self._mapping_status(p)
            self._event(p, "model.updated", model.get("notes") or "Prepared demo model selected.")
        return self.get(project_id)

    def _prepare(self, p: dict, kind: str, payload: dict, job_id: str) -> None:
        self.s.jobs.prepare(kind, "__system__", {"project_id": p["project_id"], **payload}, job_id)

    def _dispatch(self, job_id: str) -> None:
        if settings.job_backend == "vercel":
            # An interrupted publish remains pending in Lakebase and recover_dispatches
            # republishes it on the next request with the same idempotency key.
            self.s.jobs.dispatch(job_id)
        else:
            context = copy_context()
            self._executor.submit(context.run, self._run_local, job_id)

    def _run_local(self, job_id: str) -> None:
        job = self.s.store.kv_get(f"job:{job_id}")
        try:
            self.s.jobs._perform(job)
            self.s.store.kv_set(f"job:{job_id}", {**job, "status": "done"})
        except Exception:
            log.exception("Local product job failed: %s", job_id)

    def start_extraction(self, project_id: str) -> dict:
        with self._mutate(project_id) as p:
            if p["status"] == "extracting":
                return self._public(p)
            if not any(d["kind"] != "model" for d in p["documents"]):
                raise invalid("Upload a blueprint or requirements document first.")
            self._invalidate(p)
            jid = _id("extract-product")
            p["_extract_job"] = jid
            p["status"] = "extracting"
            self._event(p, "extraction.queued", "Document reading and part discovery queued.")
            self._prepare(p, "product_extract", {"job_id": jid, "input_version": p["input_version"]}, jid)
        self._dispatch(jid)
        return self.get(project_id)
