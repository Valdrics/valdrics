from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.modules.enforcement.domain.action_errors import EnforcementDomainError

HttpExceptionHandler = Callable[[Request, HTTPException], Awaitable[JSONResponse]]


def build_http_exception(exc: EnforcementDomainError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.detail,
        headers=exc.headers,
    )


async def enforcement_domain_exception_handler(
    request: Request,
    exc: EnforcementDomainError,
    http_handler: HttpExceptionHandler,
) -> JSONResponse:
    """Translate enforcement domain failures into the shared HTTP boundary."""
    return await http_handler(request, build_http_exception(exc))


def register_enforcement_domain_exception_handler(
    app: FastAPI,
    http_handler: HttpExceptionHandler,
) -> None:
    """Register the enforcement exception boundary without growing app bootstrap."""

    @app.exception_handler(EnforcementDomainError)
    async def _enforcement_domain_exception_handler(
        request: Request, exc: EnforcementDomainError
    ) -> JSONResponse:
        return await enforcement_domain_exception_handler(request, exc, http_handler)
