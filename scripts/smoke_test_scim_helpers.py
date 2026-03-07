"""Helper primitives for SCIM smoke test runner."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import httpx


SCIM_SMOKE_RECOVERABLE_EXCEPTIONS = (
    httpx.HTTPError,
    json.JSONDecodeError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    status_code: int | None = None
    detail: str | None = None
    duration_ms: float | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_url(value: str, *, name: str) -> str:
    url = str(value or "").strip()
    if not url:
        raise SystemExit(f"{name} is required.")
    return url.rstrip("/")


def auth_headers(token: str) -> dict[str, str]:
    token = str(token or "").strip()
    if not token:
        raise SystemExit("VALDRICS_SCIM_TOKEN/--scim-token is required.")
    return {"Authorization": f"Bearer {token}"}


def extract_scim_error_detail(payload: Any) -> str:
    if not payload or not isinstance(payload, dict):
        return ""
    for key in ("detail", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def safe_json(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except json.JSONDecodeError:
        return None


def scim_url(base: str, path: str) -> str:
    # Ensure urljoin keeps /scim/v2 root.
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


def record_check(
    checks: list[Check],
    *,
    name: str,
    resp: httpx.Response | None,
    started: float,
    ok: bool,
    detail: str | None = None,
) -> None:
    duration_ms = (time.time() - started) * 1000.0
    status_code = resp.status_code if resp is not None else None
    checks.append(
        Check(
            name=name,
            passed=bool(ok),
            status_code=status_code,
            detail=detail,
            duration_ms=round(duration_ms, 2),
        )
    )


def require_success(resp: httpx.Response) -> tuple[bool, str | None]:
    if resp.is_success:
        return True, None
    payload = safe_json(resp)
    detail = extract_scim_error_detail(payload) or resp.text
    return False, detail.strip() if isinstance(detail, str) else None


def build_user_payload(email: str) -> dict[str, Any]:
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": email,
        "active": True,
        "emails": [{"value": email, "primary": True}],
    }


def build_group_payload(display_name: str) -> dict[str, Any]:
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "displayName": display_name,
        "members": [],
    }


def build_group_add_member_patch(user_id: str) -> dict[str, Any]:
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "add",
                "path": "members",
                "value": [{"value": user_id}],
            }
        ],
    }


def write_out(path: str, payload: dict[str, Any]) -> None:
    if not path:
        return
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
