#!/usr/bin/env python3
"""Enforce Cloudflare Bot Fight Mode prerequisites before expensive release jobs."""

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

CLOUDFLARE_API_BASE_URL = "https://api.cloudflare.com/client/v4"
CLOUDFLARE_API_USER_AGENT = "CloudSentinel-AI-release-preflight/1.0"


def _request_json(
    url: str,
    *,
    api_token: str,
    method: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    encoded_payload = None
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_token}",
        "User-Agent": CLOUDFLARE_API_USER_AGENT,
    }
    if payload is not None:
        encoded_payload = json.dumps(payload, sort_keys=True).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        url,
        data=encoded_payload,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        permission_hint = ""
        if exc.code in {401, 403}:
            permission_hint = (
                " CLOUDFLARE_API_TOKEN must include Zone > Bot Management > Edit "
                "for the target zone."
            )
        raise RuntimeError(
            f"Cloudflare API returned HTTP {exc.code} for {method} {url}: "
            f"{body}{permission_hint}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(
            f"Cloudflare API request failed for {method} {url}: {exc}"
        ) from exc


def enforce_bot_fight_mode_disabled(
    *,
    cloudflare_zone_id: str,
    cloudflare_api_token: str,
) -> dict[str, str]:
    zone_id = cloudflare_zone_id.strip()
    if not zone_id:
        raise ValueError("CLOUDFLARE_ZONE_ID is required")

    api_token = cloudflare_api_token.strip()
    if not api_token:
        raise ValueError("CLOUDFLARE_API_TOKEN is required")

    url = (
        f"{CLOUDFLARE_API_BASE_URL}/zones/{quote(zone_id)}/bot_management"
    )
    payload = _request_json(
        url,
        api_token=api_token,
        method="PUT",
        payload={"fight_mode": False},
    )
    if not isinstance(payload, dict):
        raise ValueError("Cloudflare Bot Management update returned an unexpected payload")
    if payload.get("success") is not True:
        raise ValueError(
            "Cloudflare Bot Management update did not succeed: "
            + json.dumps(payload.get("errors", payload), sort_keys=True)
        )

    result = payload.get("result")
    if not isinstance(result, dict):
        raise ValueError("Cloudflare Bot Management update did not return result")
    if result.get("fight_mode") is not False:
        raise ValueError(
            "Cloudflare Bot Fight Mode is still enabled after update; "
            "public API health probes and users can still be challenged."
        )

    return {
        "cloudflare_zone_id": zone_id,
        "fight_mode": "false",
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
        description=(
            "Disable Cloudflare Bot Fight Mode before release jobs that expose "
            "public API health checks."
        )
    )
    parser.add_argument("--cloudflare-zone-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = enforce_bot_fight_mode_disabled(
            cloudflare_zone_id=str(args.cloudflare_zone_id),
            cloudflare_api_token=os.environ.get("CLOUDFLARE_API_TOKEN", ""),
        )
    except (RuntimeError, ValueError) as exc:
        print(
            "::error title=Cloudflare Bot Management preflight failed::"
            f"{exc}",
            file=sys.stderr,
        )
        return 1

    _write_github_output(result)
    print(
        "[cloudflare-bot-management-preflight] ok "
        f"cloudflare_zone_id={result['cloudflare_zone_id']} "
        "fight_mode=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
