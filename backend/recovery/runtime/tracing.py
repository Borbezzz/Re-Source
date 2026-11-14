"""MLflow 3 tracing to the Databricks experiment (PRD §11 observability, FR-14).

Application domain events and MLflow diagnostic traces are separate; events carry `trace_id` links.
Tracing failures never break the product path.
"""

from __future__ import annotations

import contextlib
import logging
import os
from typing import Any, Iterator, Optional

from ..config import settings

log = logging.getLogger("recovery.tracing")
_state: dict[str, Any] = {"enabled": False, "error": None, "experiment_id": None}


def init_tracing() -> dict[str, Any]:
    if not settings.tracing_enabled or not settings.mlflow_tracking_uri:
        _state.update(enabled=False, error="tracing disabled or MLFLOW_TRACKING_URI unset")
        return dict(_state)
    try:
        import mlflow

        if settings.mlflow_tracking_uri == "databricks":
            os.environ.setdefault("DATABRICKS_HOST", settings.databricks_host)
            if settings.databricks_token:
                os.environ.setdefault("DATABRICKS_TOKEN", settings.databricks_token)
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        if settings.mlflow_experiment_id:
            mlflow.set_experiment(experiment_id=settings.mlflow_experiment_id)
        with contextlib.suppress(Exception):
            mlflow.openai.autolog()
        _state.update(enabled=True, error=None, experiment_id=settings.mlflow_experiment_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("MLflow tracing unavailable: %s", exc)
        _state.update(enabled=False, error=str(exc)[:300])
    return dict(_state)


def tracing_state() -> dict[str, Any]:
    return dict(_state)


@contextlib.contextmanager
def span(name: str, span_type: str = "CHAIN", attributes: Optional[dict] = None, inputs: Optional[dict] = None) -> Iterator[Any]:
    if not _state["enabled"]:
        yield None
        return
    try:
        import mlflow

        cm = mlflow.start_span(name=name, span_type=span_type, attributes=attributes or {})
    except Exception:  # noqa: BLE001
        yield None
        return
    with cm as s:
        if inputs is not None:
            with contextlib.suppress(Exception):
                s.set_inputs(inputs)
        yield s


def current_trace_id() -> Optional[str]:
    if not _state["enabled"]:
        return None
    try:
        import mlflow

        s = mlflow.get_current_active_span()
        return s.request_id if s is not None else None
    except Exception:  # noqa: BLE001
        return None
