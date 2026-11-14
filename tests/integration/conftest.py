"""Service-level fixtures: an isolated Services container per test (temp SQLite store + checkpoints),
deterministic structured extraction, no model/Linkup/Databricks/MLflow calls, no presentation pacing.

`recovery.config.settings` may already be imported by tests/conftest.py, so offline settings are applied
by overriding the (frozen) settings object directly rather than relying on environment variables.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

OFFLINE = dict(pacing_ms=0, model_enabled=False, extraction_backend="structured", linkup_enabled=False, tracing_enabled=False,
               databricks_enabled=False, projection_enabled=False, companies_house_enabled=False, prewarm=False)


@pytest.fixture()
def offline_settings(tmp_path):
    from recovery.config import settings

    saved = {k: getattr(settings, k) for k in [*OFFLINE, "var_dir"]}
    for k, v in OFFLINE.items():
        object.__setattr__(settings, k, v)
    object.__setattr__(settings, "var_dir", tmp_path)
    yield settings
    for k, v in saved.items():
        object.__setattr__(settings, k, v)


@pytest.fixture()
def svc(tmp_path, offline_settings):
    from recovery.services.container import Services

    s = Services(db_url=f"sqlite:///{tmp_path}/op.sqlite3", start_worker=False)
    yield s
    s.coordinator.wait_idle(60)
    s.stop()
