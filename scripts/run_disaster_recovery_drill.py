#!/usr/bin/env python3
"""Execute a repeatable repository-managed disaster recovery drill against a running API."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import httpx

from app.shared.core.auth import create_access_token
from scripts.env_generation_common import (
    ensure_parent_dir,
    promote_staged_file,
    repo_root_for,
    resolve_cli_path_from_root,
    stage_json_file,
)

def _repo_root() -> Path:
    return repo_root_for(__file__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a DR drill against a rebuilt application instance."
    )
    parser.add_argument("--url", required=True, help="Base URL for the API under test.")
    parser.add_argument(
        "--out",
        default="",
        help="Optional path for a JSON evidence report.",
    )
    parser.add_argument(
        "--max-duration-seconds",
        type=int,
        default=1200,
        help="Fail if the rebuild-and-verify drill exceeds this duration.",
    )
    return parser.parse_args(argv)


def _resolve_output_path(value: str) -> Path:
    resolved = resolve_cli_path_from_root(
        _repo_root(),
        Path(value),
        field_name="out",
    )
    if resolved.exists() and not resolved.is_file():
        raise ValueError(f"out must be a file path: {resolved}")
    ensure_parent_dir(resolved, field_name="out")
    return resolved


async def _request_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, object] | None = None,
) -> tuple[int, object]:
    response = await client.request(method, url, headers=headers, json=json_body)
    try:
        payload: object = response.json()
    except (ValueError, json.JSONDecodeError):
        payload = response.text
    return int(response.status_code), payload


async def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    try:
        output_path = _resolve_output_path(str(args.out)) if args.out else None
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    started_at = datetime.now(timezone.utc)
    monotonic_start = time.perf_counter()
    base_url = str(args.url).rstrip("/")
    user_id = str(uuid4())
    email = f"dr-drill-{user_id[:8]}@valdrics.local"
    token = create_access_token(
        {"sub": user_id, "email": email},
        timedelta(hours=2),
    )
    headers = {"Authorization": f"Bearer {token}"}
    today = date.today()
    start_date = (today - timedelta(days=30)).isoformat()
    end_date = today.isoformat()

    timeout = httpx.Timeout(20.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        live_status, live_payload = await _request_json(
            client,
            "GET",
            f"{base_url}/health/live",
        )
        health_status, health_payload = await _request_json(
            client,
            "GET",
            f"{base_url}/health",
        )
        onboard_status, onboard_payload = await _request_json(
            client,
            "POST",
            f"{base_url}/api/v1/settings/onboard",
            headers=headers,
            json_body={
                "tenant_name": "Disaster Recovery Drill Tenant",
                "admin_email": email,
            },
        )
        costs_status, costs_payload = await _request_json(
            client,
            "GET",
            f"{base_url}/api/v1/costs?start_date={start_date}&end_date={end_date}",
            headers=headers,
        )

    evidence = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "started_at": started_at.isoformat(),
        "target_url": base_url,
        "regional_recovery_mode": "manual_restore_redeploy_reroute",
        "regional_recovery_contract_scope": "repository_managed_application_surface",
        "regional_recovery_rto_seconds": int(args.max_duration_seconds),
        "regional_recovery_rpo_contract": "provider_backup_restore_external_to_repository",
        "regional_recovery_rehearsal_cadence": "monthly",
        "steps": {
            "health_live": {"status_code": live_status, "payload": live_payload},
            "health_deep": {"status_code": health_status, "payload": health_payload},
            "tenant_onboard": {
                "status_code": onboard_status,
                "payload": onboard_payload,
            },
            "costs_query": {"status_code": costs_status, "payload": costs_payload},
        },
    }
    duration_seconds = round(time.perf_counter() - monotonic_start, 3)
    evidence["duration_seconds"] = duration_seconds
    evidence["rebuild_and_verify_objective_seconds"] = int(args.max_duration_seconds)

    if output_path is not None:
        try:
            staged_path = stage_json_file(output_path, evidence, indent=2, sort_keys=True)
            promote_staged_file(staged_path, output_path)
        except OSError as exc:
            raise SystemExit(f"Failed to write disaster recovery evidence: {exc}") from exc

    print(json.dumps(evidence, indent=2, sort_keys=True))

    failing = {
        name: step["status_code"]
        for name, step in evidence["steps"].items()
        if int(step["status_code"]) >= 400
    }
    if failing:
        raise SystemExit(f"Disaster recovery drill failed: {failing}")
    if duration_seconds > int(args.max_duration_seconds):
        raise SystemExit(
            "Disaster recovery drill exceeded rebuild-and-verify objective: "
            f"{duration_seconds}s > {int(args.max_duration_seconds)}s"
        )


if __name__ == "__main__":
    asyncio.run(main())
