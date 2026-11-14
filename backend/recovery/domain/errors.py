"""Typed domain errors mapped to the PRD §7 error envelope {code,message,retryable,case_revision,details,correlation_id}."""

from __future__ import annotations

from typing import Any, Optional


class DomainError(Exception):
    def __init__(self, status: int, code: str, message: str, *, retryable: bool = False, case_revision: Optional[int] = None,
                 details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable
        self.case_revision = case_revision
        self.details = details or {}


def stale(message: str, case_revision: Optional[int] = None, **details: Any) -> DomainError:
    return DomainError(409, "STALE_DECISION", message, case_revision=case_revision, details=details)


def conflict(code: str, message: str, case_revision: Optional[int] = None, **details: Any) -> DomainError:
    return DomainError(409, code, message, case_revision=case_revision, details=details)


def invalid(message: str, **details: Any) -> DomainError:
    return DomainError(422, "INVALID_INPUT", message, details=details)


def not_found(what: str) -> DomainError:
    return DomainError(404, "NOT_FOUND", f"{what} not found")


def unavailable(message: str, **details: Any) -> DomainError:
    return DomainError(503, "DEPENDENCY_UNAVAILABLE", message, retryable=True, details=details)
