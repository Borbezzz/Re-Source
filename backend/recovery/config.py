"""Runtime configuration. All secrets come from the environment (or a local, gitignored .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env", override=False)


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    repo_root: Path = REPO_ROOT
    data_dir: Path = REPO_ROOT / "data"
    rules_dir: Path = REPO_ROOT / "rules"
    templates_dir: Path = REPO_ROOT / "templates"
    var_dir: Path = field(default_factory=lambda: Path(os.getenv("RS_VAR_DIR", str(REPO_ROOT / "var"))))
    fixture_version: str = os.getenv("RS_FIXTURE_VERSION", "seed-v1")
    manifest_id: str = os.getenv("RS_MANIFEST", "engine-demo-001")

    # Operational store (Lakebase Postgres when configured, local SQLite otherwise).
    operational_db_url: str = os.getenv("RS_OPERATIONAL_DB_URL", "")

    # Models (the app's own OpenAI key; never used for building the app).
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "") or "gpt-5.4-mini"
    model_enabled: bool = _bool("RS_MODEL_ENABLED", True)
    model_timeout_s: float = float(os.getenv("RS_MODEL_TIMEOUT_S", "45"))

    # Databricks
    databricks_host: str = os.getenv("DATABRICKS_HOST", "")
    databricks_server_hostname: str = os.getenv("DATABRICKS_SERVER_HOSTNAME", "") or os.getenv("DATABRICKS_HOST", "").replace("https://", "").rstrip("/")
    # Databricks Apps inject the warehouse ID from the app resource; derive the HTTP path from it.
    databricks_http_path: str = os.getenv("DATABRICKS_HTTP_PATH", "") or (
        f"/sql/1.0/warehouses/{os.getenv('RS_WAREHOUSE_ID')}" if os.getenv("RS_WAREHOUSE_ID") else "")
    databricks_token: str = os.getenv("DATABRICKS_TOKEN", "")
    databricks_client_id: str = os.getenv("DATABRICKS_CLIENT_ID", "")
    databricks_client_secret: str = os.getenv("DATABRICKS_CLIENT_SECRET", "")
    databricks_catalog: str = os.getenv("DATABRICKS_CATALOG", "workspace")
    databricks_schema: str = os.getenv("DATABRICKS_SCHEMA", "resource")
    databricks_enabled: bool = _bool("RS_DATABRICKS_ENABLED", True)
    extraction_backend: str = os.getenv("RS_EXTRACTION_BACKEND", "auto")  # auto|databricks|openai|fixture
    projection_enabled: bool = _bool("RS_DELTA_PROJECTION", True)

    # MLflow
    mlflow_tracking_uri: str = os.getenv("MLFLOW_TRACKING_URI", "")
    mlflow_experiment_id: str = os.getenv("MLFLOW_EXPERIMENT_ID", "")
    tracing_enabled: bool = _bool("RS_TRACING", True)

    # External discovery
    linkup_api_key: str = os.getenv("LINKUP_API_KEY", "")
    linkup_enabled: bool = _bool("RS_LINKUP_ENABLED", True)
    companies_house_api_key: str = os.getenv("COMPANIES_HOUSE_API_KEY", "")
    companies_house_enabled: bool = _bool("RS_COMPANIES_HOUSE_ENABLED", True)

    # Budgets / concurrency (PRD FR-05, §8.1)
    followup_attempts_per_candidate: int = int(os.getenv("RS_FOLLOWUP_ATTEMPTS", "2"))
    run_tool_budget: int = int(os.getenv("RS_RUN_TOOL_BUDGET", "80"))
    max_case_workers: int = int(os.getenv("RS_MAX_CASE_WORKERS", "3"))
    outbox_max_attempts: int = int(os.getenv("RS_OUTBOX_MAX_ATTEMPTS", "5"))
    pacing_ms: int = int(os.getenv("RS_PACING_MS", "350"))  # presentation pacing between visible steps
    prewarm: bool = _bool("RS_PREWARM", True)  # warm SQL warehouse + extraction cache at startup (PRD §11)

    # Frontend static bundle served by the BFF in deployment
    frontend_dist: Path = REPO_ROOT / "frontend" / "dist"

    @property
    def sqlite_path(self) -> Path:
        return self.var_dir / "operational.sqlite3"

    @property
    def checkpoint_path(self) -> Path:
        return self.var_dir / "checkpoints.sqlite3"

    @property
    def db_url(self) -> str:
        return self.operational_db_url or f"sqlite:///{self.sqlite_path}"

    @property
    def databricks_configured(self) -> bool:
        has_auth = bool(self.databricks_token or (self.databricks_client_id and self.databricks_client_secret))
        return self.databricks_enabled and bool(self.databricks_server_hostname and self.databricks_http_path and has_auth)

    @property
    def model_configured(self) -> bool:
        return self.model_enabled and bool(self.openai_api_key)


settings = Settings()
settings.var_dir.mkdir(parents=True, exist_ok=True)
