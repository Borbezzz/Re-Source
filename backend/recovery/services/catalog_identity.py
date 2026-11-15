"""Persist and resolve a run's manifest identity without a mutable global catalog."""

from __future__ import annotations

import hashlib
from typing import Any

from ..adapters import store as st
from ..domain.errors import conflict, not_found


def identity(catalog: Any) -> dict:
    """Identify the loaded manifest; this hash is not a fingerprint of rules or evidence."""
    digest = hashlib.sha256(st.dumps(catalog.manifest).encode("utf-8")).hexdigest()
    return {"manifest_id": catalog.engine["engine_id"], "manifest_version": catalog.manifest["manifest_version"],
            "fixture_version": catalog.fixture_version, "manifest_sha256": digest}


def resolve(services: Any, run_id: str) -> Any:
    """Resolve only a run whose recorded manifest exactly matches the loaded catalog.

    Legacy runs have no immutable manifest digest. They need an explicit migration
    before this resolver can safely serve them; never guess from the current catalog.
    """
    if not services.store.get_run(run_id):
        raise not_found("run")
    recorded = services.store.kv_get(f"run_catalog:{run_id}")
    if recorded is None:
        raise conflict("CATALOG_IDENTITY_UNAVAILABLE", "This run predates catalog identity recording")
    if recorded != identity(services.catalog):
        raise conflict("CATALOG_IDENTITY_MISMATCH", "The run's recorded manifest is not the loaded catalog")
    return services.catalog
