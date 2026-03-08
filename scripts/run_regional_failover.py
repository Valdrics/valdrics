#!/usr/bin/env python3
"""Promote a warm-standby secondary region and cut API traffic over via Cloudflare."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Promote a secondary-region DB replica and cut the API DNS record over "
            "to the recovered regional stack."
        )
    )
    parser.add_argument("--secondary-region", required=True)
    parser.add_argument("--secondary-db-instance-id", required=True)
    parser.add_argument("--secondary-api-origin", required=True)
    parser.add_argument("--api-record-name", required=True)
    parser.add_argument("--cloudflare-zone-id", required=True)
    parser.add_argument("--cloudflare-dns-record-id", required=True)
    parser.add_argument("--out", default="")
    parser.add_argument("--max-promotion-wait-seconds", type=int, default=1800)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def _normalize_origin(origin: str) -> str:
    normalized = str(origin or "").strip().rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("secondary API origin must be an explicit http(s) origin")
    return normalized


def _build_cloudflare_headers(api_token: str) -> dict[str, str]:
    token = str(api_token or "").strip()
    if len(token) < 20:
        raise ValueError("CLOUDFLARE_API_TOKEN must be set for regional failover cutover")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _build_cloudflare_dns_payload(
    *,
    record_name: str,
    target_origin: str,
) -> dict[str, object]:
    normalized_origin = _normalize_origin(target_origin)
    parsed = urlparse(normalized_origin)
    hostname = str(parsed.hostname or "").strip()
    if not hostname:
        raise ValueError("secondary API origin must include a hostname")
    return {
        "type": "CNAME",
        "name": str(record_name or "").strip(),
        "content": hostname,
        "ttl": 1,
        "proxied": True,
    }


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


def _get_rds_client(*, region_name: str) -> Any:
    import boto3

    return boto3.client("rds", region_name=region_name)


def _describe_db_instance(rds_client: Any, *, db_instance_id: str) -> dict[str, Any]:
    response = rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_id)
    instances = list(response.get("DBInstances", []) or [])
    if not instances:
        raise RuntimeError(f"RDS instance not found: {db_instance_id}")
    return dict(instances[0])


def _is_promotion_complete(instance: dict[str, Any]) -> bool:
    status = str(instance.get("DBInstanceStatus") or "").strip().lower()
    replica_source = str(instance.get("ReadReplicaSourceDBInstanceIdentifier") or "").strip()
    return status == "available" and not replica_source


def _wait_for_replica_promotion(
    rds_client: Any,
    *,
    db_instance_id: str,
    max_wait_seconds: int,
    monotonic_fn: Any = time.monotonic,
    sleep_fn: Any = time.sleep,
) -> dict[str, Any]:
    deadline = monotonic_fn() + max_wait_seconds
    latest = _describe_db_instance(rds_client, db_instance_id=db_instance_id)
    while monotonic_fn() <= deadline:
        latest = _describe_db_instance(rds_client, db_instance_id=db_instance_id)
        if _is_promotion_complete(latest):
            return latest
        sleep_fn(15)
    raise RuntimeError(
        f"Timed out waiting for replica promotion: {db_instance_id} after {max_wait_seconds}s"
    )


async def _assert_secondary_api_live(
    client: httpx.AsyncClient,
    *,
    secondary_api_origin: str,
) -> tuple[int, object]:
    return await _request_json(
        client,
        "GET",
        f"{_normalize_origin(secondary_api_origin)}/health/live",
    )


async def _cutover_cloudflare_dns(
    client: httpx.AsyncClient,
    *,
    api_token: str,
    zone_id: str,
    dns_record_id: str,
    record_name: str,
    secondary_api_origin: str,
) -> tuple[int, object]:
    url = (
        "https://api.cloudflare.com/client/v4/zones/"
        f"{zone_id}/dns_records/{dns_record_id}"
    )
    return await _request_json(
        client,
        "PATCH",
        url,
        headers=_build_cloudflare_headers(api_token),
        json_body=_build_cloudflare_dns_payload(
            record_name=record_name,
            target_origin=secondary_api_origin,
        ),
    )


async def main() -> None:
    args = _parse_args()
    started_at = datetime.now(timezone.utc)
    monotonic_start = time.perf_counter()

    evidence: dict[str, Any] = {
        "captured_at": started_at.isoformat(),
        "secondary_region": args.secondary_region,
        "secondary_db_instance_id": args.secondary_db_instance_id,
        "secondary_api_origin": _normalize_origin(args.secondary_api_origin),
        "regional_recovery_mode": "automated_secondary_region_failover",
        "regional_recovery_contract_scope": "repository_managed_application_surface",
        "regional_recovery_rpo_contract": "provider_backup_restore_external_to_repository",
        "regional_recovery_cutover": "cloudflare_api_dns_update",
        "dry_run": bool(args.dry_run),
        "steps": {},
    }

    if args.dry_run:
        evidence["steps"] = {
            "promote_replica": {"mode": "dry_run", "db_instance_id": args.secondary_db_instance_id},
            "health_live": {"mode": "dry_run", "url": f"{evidence['secondary_api_origin']}/health/live"},
            "cutover_dns": {
                "mode": "dry_run",
                "record_name": args.api_record_name,
                "target_origin": evidence["secondary_api_origin"],
            },
        }
    else:
        api_token = str(os.getenv("CLOUDFLARE_API_TOKEN", "") or "").strip()
        rds_client = _get_rds_client(region_name=args.secondary_region)
        rds_client.promote_read_replica(DBInstanceIdentifier=args.secondary_db_instance_id)
        promoted_instance = _wait_for_replica_promotion(
            rds_client,
            db_instance_id=args.secondary_db_instance_id,
            max_wait_seconds=int(args.max_promotion_wait_seconds),
        )
        evidence["steps"]["promote_replica"] = {
            "status": "completed",
            "db_instance_arn": promoted_instance.get("DBInstanceArn"),
            "db_instance_status": promoted_instance.get("DBInstanceStatus"),
            "engine": promoted_instance.get("Engine"),
            "endpoint": (
                (promoted_instance.get("Endpoint") or {}).get("Address")
                if isinstance(promoted_instance.get("Endpoint"), dict)
                else None
            ),
        }

        timeout = httpx.Timeout(20.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            health_status, health_payload = await _assert_secondary_api_live(
                client,
                secondary_api_origin=str(evidence["secondary_api_origin"]),
            )
            evidence["steps"]["health_live"] = {
                "status_code": health_status,
                "payload": health_payload,
            }
            if health_status >= 400:
                raise SystemExit(
                    f"Secondary API health check failed before cutover: {health_status}"
                )

            dns_status, dns_payload = await _cutover_cloudflare_dns(
                client,
                api_token=api_token,
                zone_id=args.cloudflare_zone_id,
                dns_record_id=args.cloudflare_dns_record_id,
                record_name=args.api_record_name,
                secondary_api_origin=str(evidence["secondary_api_origin"]),
            )
            evidence["steps"]["cutover_dns"] = {
                "status_code": dns_status,
                "payload": dns_payload,
            }
            if dns_status >= 400:
                raise SystemExit(f"Cloudflare DNS cutover failed: {dns_status}")

    duration_seconds = round(time.perf_counter() - monotonic_start, 3)
    evidence["duration_seconds"] = duration_seconds
    evidence["captured_at"] = datetime.now(timezone.utc).isoformat()

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(evidence, handle, indent=2, sort_keys=True)

    print(json.dumps(evidence, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
