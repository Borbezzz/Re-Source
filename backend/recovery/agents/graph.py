"""LangGraph state machine (PRD §8.1) with a persistent checkpointer (FR-14).

One graph serves first investigations and targeted reassessments; the reassessment entry is the same
graph with `affected_candidate_ids` set so unaffected candidates reuse prior results by reference.
"""

from __future__ import annotations

import sqlite3
from typing import Annotated, Any, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from ..config import settings
from .investigation import InvestigationNodes


def merge(a: Optional[dict], b: Optional[dict]) -> dict:
    return {**(a or {}), **(b or {})}


def add_usage(a: Optional[dict], b: Optional[dict]) -> dict:
    out = dict(a or {})
    for k, v in (b or {}).items():
        out[k] = out.get(k, 0) + v
    return out


class GraphState(TypedDict, total=False):
    run_id: str
    case_id: str
    generation_id: str
    kind: str
    trigger_id: Optional[str]
    trigger: Optional[dict]
    mode: str
    affected_candidate_ids: Optional[list]
    input_revision: int
    prev_decision: Optional[dict]
    requirement_set_id: str
    requirements: list
    now: str
    signals: list
    offers: Annotated[dict, merge]
    public_leads: Annotated[dict, merge]
    docs: Annotated[dict, merge]
    facts: Annotated[dict, merge]
    extraction_modes: Annotated[dict, merge]
    checks: Annotated[dict, merge]
    gaps: Annotated[dict, merge]
    followups_used: dict
    eligibility: dict
    ranked: list
    tasks: Annotated[dict, merge]
    tool_usage: Annotated[dict, add_usage]
    decision_id: str
    decision_status: str


def build_graph(services: Any, checkpointer: Any = None):  # noqa: ANN201
    n = InvestigationNodes(services)
    g = StateGraph(GraphState)
    g.add_node("load_case", n.load_case)
    g.add_node("snapshot_requirements", n.snapshot_requirements)
    g.add_node("source_buy", n.source_buy)
    g.add_node("source_make", n.source_make)
    g.add_node("normalize_offers", n.normalize_offers)
    g.add_node("extract_and_validate", n.extract_and_validate)
    g.add_node("supplier_site_checks", n.supplier_site_checks)
    g.add_node("technical_checks", n.technical_checks)
    g.add_node("regulatory_route", n.regulatory_route)
    g.add_node("resolve_gaps_if_budget", n.resolve_gaps_if_budget)
    g.add_node("evaluate_eligibility", n.evaluate_eligibility)
    g.add_node("schedule_and_rank", n.schedule_and_rank)
    g.add_node("persist_decision", n.persist_decision)
    g.add_edge(START, "load_case")
    g.add_edge("load_case", "snapshot_requirements")
    g.add_edge("snapshot_requirements", "source_buy")
    g.add_edge("snapshot_requirements", "source_make")
    g.add_edge(["source_buy", "source_make"], "normalize_offers")
    g.add_edge("normalize_offers", "extract_and_validate")
    for node in ("supplier_site_checks", "technical_checks", "regulatory_route"):
        g.add_edge("extract_and_validate", node)
    g.add_edge(["supplier_site_checks", "technical_checks", "regulatory_route"], "resolve_gaps_if_budget")
    g.add_edge("resolve_gaps_if_budget", "evaluate_eligibility")
    g.add_edge("evaluate_eligibility", "schedule_and_rank")
    g.add_edge("schedule_and_rank", "persist_decision")
    g.add_edge("persist_decision", END)
    return g.compile(checkpointer=checkpointer)


def make_checkpointer() -> tuple[Any, str]:
    """One graph-checkpoint authority. SQLite file locally; Postgres (Lakebase) when configured."""
    if settings.db_url.startswith("postgresql"):
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg import sql
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool
        from sqlalchemy.engine import make_url
        from ..adapters.lakebase import token_provider

        url = make_url(settings.db_url)
        def connection_kwargs():
            return {"host": url.host, "port": url.port or 5432, "user": url.username,
                    "dbname": url.database, "password": url.password or token_provider(),
                    "sslmode": url.query.get("sslmode", "require"), "autocommit": True,
                    "prepare_threshold": 0, "row_factory": dict_row}
        def configure(conn):
            conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(settings.lakebase_schema)))
            conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(settings.lakebase_schema)))
        pool = ConnectionPool(kwargs=connection_kwargs, configure=configure, min_size=0, max_size=4,
                              max_lifetime=1800, timeout=30, open=True)
        saver = PostgresSaver(pool)
        # Multiple cold HTTP/queue instances may initialise simultaneously.
        # Serialise checkpoint DDL/migration records, not normal graph writes.
        with pool.connection() as setup_conn:
            setup_conn.execute("SELECT pg_advisory_lock(hashtextextended('resource:checkpoint-schema', 0))")
            try:
                saver.setup()
            finally:
                setup_conn.execute("SELECT pg_advisory_unlock(hashtextextended('resource:checkpoint-schema', 0))")
        return saver, "postgres"
    from langgraph.checkpoint.sqlite import SqliteSaver

    conn = sqlite3.connect(str(settings.checkpoint_path), check_same_thread=False)
    return SqliteSaver(conn), "sqlite"
