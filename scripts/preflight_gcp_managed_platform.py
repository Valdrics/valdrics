#!/usr/bin/env python3
"""Fail-fast Google Cloud IAM checks for managed platform releases."""

from __future__ import annotations

import argparse
import json
import subprocess

DEFAULT_REQUIRED_PERMISSIONS = (
    "iam.serviceAccounts.create",
    "iam.serviceAccounts.get",
    "iam.serviceAccounts.getIamPolicy",
    "iam.serviceAccounts.setIamPolicy",
    "resourcemanager.projects.getIamPolicy",
    "resourcemanager.projects.setIamPolicy",
)


def _parse_granted_permissions(raw_payload: str) -> set[str]:
    try:
        payload = json.loads(raw_payload or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"gcloud permissions response was not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("gcloud permissions response must be a JSON object")
    permissions = payload.get("permissions", [])
    if permissions is None:
        permissions = []
    if not isinstance(permissions, list):
        raise ValueError("gcloud permissions response field 'permissions' must be a list")
    return {str(permission) for permission in permissions}


def _test_project_permissions(
    *, project_id: str, required_permissions: tuple[str, ...]
) -> set[str]:
    command = [
        "gcloud",
        "projects",
        "test-iam-permissions",
        project_id,
        f"--permissions={','.join(required_permissions)}",
        "--format=json",
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        raise RuntimeError(
            "gcloud projects test-iam-permissions failed"
            + (f": {stderr}" if stderr else "")
        )
    return _parse_granted_permissions(completed.stdout)


def validate_project_permissions(
    *, project_id: str, required_permissions: tuple[str, ...]
) -> dict[str, list[str]]:
    project = project_id.strip()
    if not project:
        raise ValueError("GCP project ID is required")
    if not required_permissions:
        raise ValueError("at least one required permission must be supplied")

    granted = _test_project_permissions(
        project_id=project,
        required_permissions=required_permissions,
    )
    missing = [
        permission
        for permission in required_permissions
        if permission not in granted
    ]
    if missing:
        raise RuntimeError(
            "GCP deployer is missing project IAM permissions required before "
            "Terraform can manage the unified platform: "
            + ", ".join(missing)
        )
    return {
        "granted_permissions": sorted(granted),
        "required_permissions": sorted(required_permissions),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate GCP deployer permissions before expensive release jobs."
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument(
        "--permission",
        action="append",
        dest="permissions",
        default=[],
        help=(
            "Required project IAM permission. May be provided more than once; "
            "defaults to the managed platform Terraform IAM prerequisites."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    required_permissions = tuple(args.permissions or DEFAULT_REQUIRED_PERMISSIONS)
    result = validate_project_permissions(
        project_id=str(args.project_id),
        required_permissions=required_permissions,
    )
    print(
        "[managed-platform-gcp-preflight] ok "
        f"project_id={args.project_id} "
        f"required_permissions={len(result['required_permissions'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
