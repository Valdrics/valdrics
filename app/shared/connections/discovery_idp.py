from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

import httpx

from app.shared.core.http import get_http_client


async def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    allow_404: bool = False,
    get_http_client_fn: Callable[[], httpx.AsyncClient] = get_http_client,
    attempt_values: Iterable[int] | None = None,
) -> dict[str, Any]:
    client = get_http_client_fn()
    attempts = tuple(attempt_values or range(1, 4))
    max_attempt = max(attempts, default=0)
    last_error: Exception | None = None
    for attempt in attempts:
        try:
            response = await client.request(method, url, headers=headers)
            if allow_404 and response.status_code == 404:
                return {}
            if (
                response.status_code in {429, 500, 502, 503, 504}
                and attempt < max_attempt
            ):
                continue
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
            if isinstance(payload, list):
                return {"value": payload}
            raise ValueError("invalid_payload_shape")
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt == max_attempt:
                break
    raise ValueError(f"request_failed:{url}: {last_error}")


async def scan_microsoft_enterprise_apps(
    token: str,
    *,
    request_json_fn: Any,
) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    headers = {"Authorization": f"Bearer {token}"}
    url = (
        "https://graph.microsoft.com/v1.0/servicePrincipals"
        "?$select=displayName,appId,servicePrincipalType&$top=999"
    )
    discovered_names: list[str] = []
    page_count = 0
    while url and page_count < 5:
        page_count += 1
        try:
            payload = await request_json_fn("GET", url, headers=headers)
        except ValueError as exc:
            warnings.append(f"microsoft_graph_scan_failed: {exc}")
            break

        entries = payload.get("value", [])
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                display_name = str(entry.get("displayName") or "").strip()
                if display_name:
                    discovered_names.append(display_name)

        next_link = payload.get("@odata.nextLink")
        url = str(next_link).strip() if isinstance(next_link, str) else ""

    return sorted(set(discovered_names)), warnings


async def scan_google_workspace_apps(
    token: str,
    *,
    max_users: int,
    request_json_fn: Any,
) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    headers = {"Authorization": f"Bearer {token}"}
    users_url = (
        "https://admin.googleapis.com/admin/directory/v1/users"
        "?customer=my_customer&maxResults=100&projection=basic"
    )
    try:
        users_payload = await request_json_fn("GET", users_url, headers=headers)
    except ValueError as exc:
        warnings.append(f"google_workspace_user_scan_failed: {exc}")
        return [], warnings

    users = users_payload.get("users", [])
    if not isinstance(users, list):
        users = []

    discovered_names: set[str] = set()
    sampled = 0
    permission_errors = 0
    for user in users:
        if sampled >= max_users:
            break
        if not isinstance(user, dict):
            continue
        email = str(user.get("primaryEmail") or "").strip()
        if not email:
            continue
        sampled += 1
        token_url = (
            "https://admin.googleapis.com/admin/directory/v1/users/" f"{email}/tokens"
        )
        try:
            token_payload = await request_json_fn(
                "GET", token_url, headers=headers, allow_404=True
            )
        except ValueError as exc:
            message = str(exc)
            warnings.append(f"google_workspace_token_scan_failed:{email}:{message}")
            if "status 403" in message:
                permission_errors += 1
            if permission_errors >= 3:
                warnings.append(
                    "google_workspace_token_scan_aborted: repeated 403 responses"
                )
                break
            continue

        items = token_payload.get("items", [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("displayText") or item.get("clientId") or "").strip()
            if label:
                discovered_names.add(label)

    return sorted(discovered_names), warnings
