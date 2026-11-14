"""Request identity for the public demo; propagated to durable jobs, never trusted from a header."""
from contextvars import ContextVar

visitor_id: ContextVar[str | None] = ContextVar("visitor_id", default=None)
job_run_id: ContextVar[str | None] = ContextVar("job_run_id", default=None)
PUBLIC_ACTOR = "Public demo visitor (unverified)"
