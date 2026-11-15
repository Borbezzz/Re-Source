"""Loads the versioned scenario snapshot: manifest, fixtures, requirement sets, ranking config,
applicability catalogue and template registry.

The catalog is immutable reference data for one fixture version. Run-scoped mutable state (which
evidence version is active, injected signals, follow-up evidence) lives in the operational store and
is overlaid through `RunView` (see services/run_state.py).
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..config import settings


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


@dataclass
class Catalog:
    fixture_version: str
    manifest: dict[str, Any]
    scenario: dict[str, Any]
    suppliers: dict[str, dict]
    sites: dict[str, dict]
    routes: dict[str, dict]
    geos: dict[str, dict]
    metrics: list[dict]
    offers: dict[str, dict]
    plans: dict[str, dict]
    evidence: dict[str, dict]
    signals: dict[str, dict]  # keyed by fixture_id
    evidence_changes: dict[str, dict]
    supplier_replies: list[dict]
    relationships: list[dict]
    fx: dict[str, Any]
    requirement_sets: dict[str, dict]
    requirements_version: str
    ranking: dict[str, Any]
    applicability: dict[str, Any]
    templates: dict[str, dict]
    templates_version: str
    initial_evidence_ids: frozenset = frozenset()
    components: dict[str, dict] = field(default_factory=dict)  # component_id -> manifest component
    case_to_component: dict[str, str] = field(default_factory=dict)

    # ---------------------------------------------------------------------------------------
    @property
    def engine(self) -> dict:
        return self.manifest["engine"]

    def component_for_case(self, case_id: str) -> dict:
        return self.components[self.case_to_component[case_id]]

    def offers_for_case(self, case_id: str) -> list[dict]:
        return [o for o in self.offers.values() if o["case_id"] == case_id]

    def label(self, entity_id: str, entity_type: str | None = None) -> str:
        if entity_id in self.offers:
            return self.offers[entity_id]["label"]
        if entity_id in self.sites:
            return self.sites[entity_id]["name"]
        if entity_id in self.suppliers:
            return self.suppliers[entity_id]["legal_entity_name"]
        if entity_id in self.routes:
            return self.routes[entity_id]["label"]
        if entity_id in self.geos:
            return self.geos[entity_id]["name"]
        if entity_id in self.components:
            return self.components[entity_id]["display_name"]
        if entity_id in self.case_to_component:
            return self.components[self.case_to_component[entity_id]]["display_name"] + " case"
        if entity_id in self.evidence:
            return self.evidence[entity_id]["title"]
        return entity_id

    def metric(self, site_id: str, name: str) -> dict | None:
        for m in self.metrics:
            if m["site_id"] == site_id and m["metric_name"] == name:
                return m
        return None

    def requirements_for(self, requirement_set_id: str) -> list[dict]:
        return self.requirement_sets[requirement_set_id]["resolved"]


def _resolve_requirement_sets(rules_dir: Path) -> tuple[dict[str, dict], str]:
    common = yaml.safe_load((rules_dir / "requirements" / "_common.yaml").read_text())["templates"]
    sets: dict[str, dict] = {}
    versions = []
    for path in sorted((rules_dir / "requirements").glob("RS-REQ-*.yaml")):
        spec = yaml.safe_load(path.read_text())
        resolved = []
        for item in spec["requirements"]:
            tpl = copy.deepcopy(common[item["template"]])
            params = dict(tpl.get("params", {}))
            params.update(item.get("params", {}))
            params.setdefault("part_identity", spec["part_identity"])
            resolved.append({
                "requirement_id": item["id"],
                "requirement_set_id": spec["requirement_set_id"],
                "version": spec["version"],
                "template_code": item["template"],
                "title": tpl["title"],
                "plain_language": tpl["plain_language"],
                "category": tpl["category"],
                "routes": tpl["routes"],
                "mandatory": tpl["mandatory"],
                "evaluator_id": tpl["evaluator_id"],
                "evaluator_version": tpl["evaluator_version"],
                "fact_inputs": tpl["fact_inputs"],
                "params": params,
                "evidence_authority_policy": tpl["evidence_authority_policy"],
                "feasibility_only": tpl.get("feasibility_only", False),
            })
        spec["resolved"] = resolved
        sets[spec["requirement_set_id"]] = spec
        versions.append(f"{spec['requirement_set_id']}@{spec['version']}")
    return sets, "requirements:" + ",".join(versions)


@lru_cache(maxsize=4)
def load_catalog(fixture_version: str | None = None, manifest_id: str | None = None) -> Catalog:
    fixture_version = fixture_version or settings.fixture_version
    manifest_id = manifest_id or settings.manifest_id
    fx_dir = settings.data_dir / "fixtures" / fixture_version
    manifest = _load_json(settings.data_dir / "manifests" / f"{manifest_id}.json")
    req_sets, req_version = _resolve_requirement_sets(settings.rules_dir)
    ranking = yaml.safe_load((settings.rules_dir / "ranking" / "default-v1.yaml").read_text())
    applicability = yaml.safe_load((settings.rules_dir / "applicability" / "uk-caa-v1.yaml").read_text())
    registry = yaml.safe_load((settings.templates_dir / "registry" / "registry.yaml").read_text())
    cat = Catalog(
        fixture_version=fixture_version,
        manifest=manifest,
        scenario=_load_json(fx_dir / "scenario.json"),
        suppliers={s["supplier_id"]: s for s in _load_json(fx_dir / "suppliers.json")},
        sites={s["site_id"]: s for s in _load_json(fx_dir / "sites.json")},
        routes={r["route_id"]: r for r in _load_json(fx_dir / "routes.json")},
        geos={g["geo_id"]: g for g in _load_json(fx_dir / "geos.json")},
        metrics=_load_json(fx_dir / "metrics.json"),
        offers={o["candidate_id"]: o for o in _load_json(fx_dir / "offers.json")},
        plans=_load_json(fx_dir / "plans.json"),
        evidence={e["version_id"]: e for e in _load_json(fx_dir / "evidence.json")},
        signals={s["fixture_id"]: s for s in _load_json(fx_dir / "signals.json")},
        evidence_changes={c["fixture_id"]: c for c in _load_json(fx_dir / "evidence_changes.json")},
        supplier_replies=_load_json(fx_dir / "supplier_replies.json"),
        relationships=_load_json(fx_dir / "relationships.json"),
        fx=_load_json(fx_dir / "fx.json"),
        requirement_sets=req_sets,
        requirements_version=req_version,
        ranking=ranking,
        applicability=applicability,
        templates={t["template_id"]: t for t in registry["templates"]},
        templates_version=registry["registry_version"],
    )
    cat.initial_evidence_ids = frozenset(cat.evidence.keys())
    for comp in manifest["components"]:
        cat.components[comp["component_id"]] = comp
        cat.case_to_component[comp["case_id"]] = comp["component_id"]
    # follow-up evidence (supplier replies) and evidence-change versions are addressable by ID too
    for reply in cat.supplier_replies:
        if reply.get("evidence"):
            cat.evidence.setdefault(reply["evidence"]["version_id"], reply["evidence"])
    for change in cat.evidence_changes.values():
        ev = change["new_evidence"]
        cat.evidence.setdefault(ev["version_id"], ev)
    return cat
