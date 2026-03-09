from __future__ import annotations

from typing import Any

from fastapi import HTTPException as FastAPIHTTPException


class EnforcementDomainError(FastAPIHTTPException):
    """Domain-owned enforcement error boundary decoupled from HTTP transport."""

    def __init__(
        self,
        *,
        status_code: int,
        detail: Any,
        headers: dict[str, str] | None = None,
    ):
        normalized_headers = dict(headers) if headers else None
        super().__init__(
            status_code=int(status_code),
            detail=detail,
            headers=normalized_headers,
        )

class EnforcementActionError(EnforcementDomainError):
    """Action-specific alias kept for the orchestrator surface."""
