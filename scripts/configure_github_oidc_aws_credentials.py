#!/usr/bin/env python3
"""Assume an AWS role from GitHub Actions OIDC and export short-lived credentials."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Exchange the GitHub Actions OIDC token for short-lived AWS credentials "
            "and write them to GITHUB_ENV for subsequent workflow steps."
        )
    )
    parser.add_argument("--role-arn", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument(
        "--session-name",
        default="github-actions-regional-failover",
    )
    parser.add_argument(
        "--audience",
        default="sts.amazonaws.com",
    )
    parser.add_argument("--out", default="")
    return parser.parse_args()


def _require_env(name: str) -> str:
    value = str(os.getenv(name, "") or "").strip()
    if not value:
        raise RuntimeError(f"{name} must be set for GitHub OIDC AWS credential exchange")
    return value


def _build_oidc_request_url(*, base_url: str, audience: str) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}audience={quote(audience, safe='')}"


def _fetch_github_oidc_token(
    *,
    request_url: str,
    request_token: str,
    audience: str,
    client: httpx.Client | None = None,
) -> str:
    managed_client = client or httpx.Client(timeout=httpx.Timeout(15.0, connect=5.0))
    should_close = client is None
    try:
        response = managed_client.get(
            _build_oidc_request_url(base_url=request_url, audience=audience),
            headers={"Authorization": f"Bearer {request_token}"},
        )
        response.raise_for_status()
        payload = response.json()
        token = str(payload.get("value") or "").strip()
        if not token:
            raise RuntimeError("GitHub OIDC token response did not include a token value")
        return token
    finally:
        if should_close:
            managed_client.close()


def _assume_role_with_web_identity(
    *,
    role_arn: str,
    region: str,
    session_name: str,
    web_identity_token: str,
    boto3_module: Any | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    boto3 = boto3_module
    if boto3 is None:
        import boto3 as boto3_module_import

        boto3 = boto3_module_import

    sts = boto3.client("sts", region_name=region)
    assumed = sts.assume_role_with_web_identity(
        RoleArn=role_arn,
        RoleSessionName=session_name,
        WebIdentityToken=web_identity_token,
    )
    credentials = dict(assumed.get("Credentials") or {})
    if not credentials:
        raise RuntimeError("AWS STS assume_role_with_web_identity returned no credentials")

    assumed_session = boto3.session.Session(
        aws_access_key_id=credentials.get("AccessKeyId"),
        aws_secret_access_key=credentials.get("SecretAccessKey"),
        aws_session_token=credentials.get("SessionToken"),
        region_name=region,
    )
    identity = dict(assumed_session.client("sts").get_caller_identity())
    return credentials, identity


def _write_github_env(
    *,
    github_env_path: str,
    credentials: dict[str, Any],
    region: str,
    role_arn: str,
) -> None:
    lines = [
        f"AWS_ACCESS_KEY_ID={str(credentials.get('AccessKeyId') or '').strip()}",
        f"AWS_SECRET_ACCESS_KEY={str(credentials.get('SecretAccessKey') or '').strip()}",
        f"AWS_SESSION_TOKEN={str(credentials.get('SessionToken') or '').strip()}",
        f"AWS_DEFAULT_REGION={region}",
        f"AWS_REGION={region}",
        f"FAILOVER_AWS_ROLE_TO_ASSUME={role_arn}",
    ]
    with open(github_env_path, "a", encoding="utf-8") as handle:
        for line in lines:
            handle.write(f"{line}\n")


def _build_evidence_payload(
    *,
    role_arn: str,
    region: str,
    audience: str,
    session_name: str,
    identity: dict[str, Any],
) -> dict[str, Any]:
    return {
        "role_arn": role_arn,
        "region": region,
        "audience": audience,
        "session_name": session_name,
        "assumed_identity": {
            "account": str(identity.get("Account") or "").strip(),
            "arn": str(identity.get("Arn") or "").strip(),
            "user_id": str(identity.get("UserId") or "").strip(),
        },
    }


def main() -> int:
    args = _parse_args()
    request_url = _require_env("ACTIONS_ID_TOKEN_REQUEST_URL")
    request_token = _require_env("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    github_env_path = _require_env("GITHUB_ENV")

    oidc_token = _fetch_github_oidc_token(
        request_url=request_url,
        request_token=request_token,
        audience=args.audience,
    )
    credentials, identity = _assume_role_with_web_identity(
        role_arn=args.role_arn,
        region=args.region,
        session_name=args.session_name,
        web_identity_token=oidc_token,
    )
    _write_github_env(
        github_env_path=github_env_path,
        credentials=credentials,
        region=args.region,
        role_arn=args.role_arn,
    )

    evidence = _build_evidence_payload(
        role_arn=args.role_arn,
        region=args.region,
        audience=args.audience,
        session_name=args.session_name,
        identity=identity,
    )
    if args.out:
        Path(args.out).write_text(
            json.dumps(evidence, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
