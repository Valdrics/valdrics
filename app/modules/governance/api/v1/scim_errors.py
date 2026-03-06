from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse

from app.modules.governance.api.v1.scim_schemas import SCIM_ERROR_SCHEMA


class ScimError(Exception):
    def __init__(
        self, status_code: int, detail: str, *, scim_type: str | None = None
    ) -> None:
        super().__init__(detail)
        self.status_code = int(status_code)
        self.detail = str(detail)
        self.scim_type = scim_type


def scim_error_response(exc: ScimError) -> JSONResponse:
    payload: dict[str, Any] = {
        "schemas": [SCIM_ERROR_SCHEMA],
        "status": str(exc.status_code),
        "detail": exc.detail,
    }
    if exc.scim_type:
        payload["scimType"] = exc.scim_type
    return JSONResponse(
        status_code=exc.status_code,
        content=payload,
        headers={"WWW-Authenticate": "Bearer"},
    )
