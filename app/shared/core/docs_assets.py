"""Helpers for docs page rendering with SRI hardening."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse

DOCS_ASSET_SRI_RECOVERABLE_EXCEPTIONS = (
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)


def compute_sri(file_path: str, *, logger: Any) -> str | None:
    try:
        digest = hashlib.sha384(Path(file_path).read_bytes()).digest()
        return "sha384-" + base64.b64encode(digest).decode("ascii")
    except DOCS_ASSET_SRI_RECOVERABLE_EXCEPTIONS as exc:
        logger.warning("docs_asset_sri_compute_failed", file_path=file_path, error=str(exc))
        return None


def attach_sri(content: str, *, marker: str, sri_hash: str | None) -> str:
    if not sri_hash or marker not in content:
        return content
    return content.replace(
        marker,
        f'{marker} integrity="{sri_hash}" crossorigin="anonymous"',
        1,
    )


async def render_swagger_ui_html(app: FastAPI, *, logger: Any) -> HTMLResponse:
    response = get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
        swagger_favicon_url="/static/favicon.png",
    )
    content = bytes(response.body).decode("utf-8")
    content = attach_sri(
        content,
        marker='src="/static/swagger-ui-bundle.js"',
        sri_hash=compute_sri("app/static/swagger-ui-bundle.js", logger=logger),
    )
    content = attach_sri(
        content,
        marker='href="/static/swagger-ui.css"',
        sri_hash=compute_sri("app/static/swagger-ui.css", logger=logger),
    )
    return HTMLResponse(content=content, status_code=response.status_code)


async def render_redoc_ui_html(app: FastAPI, *, logger: Any) -> HTMLResponse:
    response = get_redoc_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=app.title + " - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
        redoc_favicon_url="/static/favicon.png",
    )
    content = bytes(response.body).decode("utf-8")
    content = attach_sri(
        content,
        marker='src="/static/redoc.standalone.js"',
        sri_hash=compute_sri("app/static/redoc.standalone.js", logger=logger),
    )
    return HTMLResponse(content=content, status_code=response.status_code)
