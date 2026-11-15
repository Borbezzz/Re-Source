"""Read-only assembly profiles; research remains gated until runs own their catalog."""

from __future__ import annotations

import json
from typing import Any

from ..config import settings
from ..domain.errors import not_found
from ..domain.models import AssemblyProfile


def profiles(services: Any) -> list[dict]:
    catalog = services.catalog
    engine = catalog.engine
    current = AssemblyProfile.model_validate({
        "assembly_id": engine["engine_id"], "display_name": engine["display_name"], "product_type": "engine",
        "description": engine.get("representative_note", ""), "requirements_status": "fixture_defined",
        "investigation_available": True, "data_origin": engine.get("data_origin", "synthetic_demo"),
        "asset": engine.get("asset", {}),
        "components": [{"component_id": c["component_id"], "display_name": c["display_name"],
                        "node_name": c["mesh_mapping"]["node_name"]} for c in catalog.manifest["components"]],
    })
    result = [current.model_dump(mode="json")]
    seen = {current.assembly_id}
    for path in sorted((settings.data_dir / "assembly-profiles").glob("*.json")):
        profile = AssemblyProfile.model_validate(json.loads(path.read_text()))
        if profile.assembly_id in seen:
            raise ValueError(f"duplicate assembly profile {profile.assembly_id}")
        component_ids = [component.component_id for component in profile.components]
        node_names = [component.node_name for component in profile.components]
        if not component_ids or len(component_ids) != len(set(component_ids)) or len(node_names) != len(set(node_names)):
            raise ValueError(f"invalid component mapping in assembly profile {profile.assembly_id}")
        if profile.investigation_available or profile.requirements_status != "source_required":
            raise ValueError(f"unavailable assembly profile {profile.assembly_id} must require reviewed sources")
        seen.add(profile.assembly_id)
        result.append(profile.model_dump(mode="json"))
    return result


def get_profile(services: Any, assembly_id: str) -> dict:
    for profile in profiles(services):
        if profile["assembly_id"] == assembly_id:
            return profile
    raise not_found("assembly")
