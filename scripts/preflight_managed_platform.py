#!/usr/bin/env python3
"""Fail-fast checks for managed platform release prerequisites."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.generate_managed_deployment_artifacts import supabase_project_ref_from_url

SUPABASE_API_BASE_URL = "https://api.supabase.com"
SUPABASE_API_USER_AGENT = "CloudSentinel-AI-release-preflight/1.0"


def _load_runtime_plain_env(raw_payload: str) -> dict[str, str]:
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"runtime plain env JSON is invalid: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("runtime plain env JSON must be an object")
    return {str(key): str(value) for key, value in payload.items()}


def _request_json(url: str, *, access_token: str) -> Any:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "User-Agent": SUPABASE_API_USER_AGENT,
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Supabase API returned HTTP {exc.code} for {url}: {body}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(f"Supabase API request failed for {url}: {exc}") from exc


def _project_belongs_to_org(project: dict[str, Any], organization_id: str) -> bool:
    expected = organization_id.strip()
    return expected in {
        str(project.get("organization_id") or "").strip(),
        str(project.get("organization_slug") or "").strip(),
    }


def validate_supabase_project_binding(
    *,
    runtime_plain_env_json: str,
    supabase_organization_id: str,
    supabase_project_name: str,
    supabase_access_token: str,
) -> dict[str, str]:
    runtime_plain_env = _load_runtime_plain_env(runtime_plain_env_json)
    supabase_url = runtime_plain_env.get("SUPABASE_URL", "")
    project_ref = supabase_project_ref_from_url(supabase_url)
    if not project_ref:
        raise ValueError(
            "SUPABASE_URL must be a concrete https://<project-ref>.supabase.co URL "
            "so Terraform can import the existing Supabase project."
        )

    organization_id = supabase_organization_id.strip()
    if not organization_id:
        raise ValueError("SUPABASE_ORGANIZATION_ID is required")

    access_token = supabase_access_token.strip()
    if not access_token:
        raise ValueError("SUPABASE_ACCESS_TOKEN is required")

    project = _request_json(
        f"{SUPABASE_API_BASE_URL}/v1/projects/{quote(project_ref)}",
        access_token=access_token,
    )
    if not isinstance(project, dict):
        raise ValueError("Supabase project lookup returned an unexpected payload")

    if str(project.get("ref") or "").strip() != project_ref:
        raise ValueError(
            f"Supabase project lookup returned ref {project.get('ref')!r}, "
            f"expected {project_ref!r}"
        )
    if not _project_belongs_to_org(project, organization_id):
        raise ValueError(
            f"Supabase project {project_ref!r} is not in organization "
            f"{organization_id!r}"
        )

    actual_name = str(project.get("name") or "").strip()
    expected_name = supabase_project_name.strip()
    if expected_name and actual_name and actual_name != expected_name:
        raise ValueError(
            f"Supabase project ref {project_ref!r} is named {actual_name!r}, "
            f"but SUPABASE_PROJECT_NAME is {expected_name!r}."
        )

    return {
        "project_ref": project_ref,
        "project_name": actual_name or expected_name,
        "project_status": str(project.get("status") or "unknown"),
    }


def _write_github_output(values: dict[str, str]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT", "").strip()
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate managed platform prerequisites before expensive release jobs."
    )
    parser.add_argument("--runtime-plain-env-json", required=True)
    parser.add_argument("--supabase-organization-id", required=True)
    parser.add_argument("--supabase-project-name", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = validate_supabase_project_binding(
        runtime_plain_env_json=str(args.runtime_plain_env_json),
        supabase_organization_id=str(args.supabase_organization_id),
        supabase_project_name=str(args.supabase_project_name),
        supabase_access_token=os.environ.get("SUPABASE_ACCESS_TOKEN", ""),
    )
    _write_github_output(result)
    print(
        "[managed-platform-preflight] ok "
        f"supabase_project_ref={result['project_ref']} "
        f"supabase_project_name={result['project_name']} "
        f"supabase_project_status={result['project_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
