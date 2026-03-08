from __future__ import annotations

from typing import Any

from fastapi import HTTPException


class EnforcementDomainError(Exception):
    """Domain-owned enforcement error boundary decoupled from HTTP transport."""

    def __init__(
        self,
        *,
        status_code: int,
        detail: Any,
        headers: dict[str, str] | None = None,
    ):
        self.status_code = int(status_code)
        self.detail = detail
        self.headers = dict(headers) if headers else None
        super().__init__(self._message_text())

    def _message_text(self) -> str:
        if isinstance(self.detail, str):
            return self.detail
        if isinstance(self.detail, dict):
            message = self.detail.get("message")
            if isinstance(message, str) and message.strip():
                return message
        return "Enforcement domain error"

    def to_http_exception(self) -> HTTPException:
        return HTTPException(
            status_code=self.status_code,
            detail=self.detail,
            headers=self.headers,
        )


class EnforcementActionError(EnforcementDomainError):
    """Action-specific alias kept for the orchestrator surface."""
