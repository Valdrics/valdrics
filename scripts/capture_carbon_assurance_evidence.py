"""
Capture carbon assurance evidence (methodology + factor versions) into audit logs.
"""

from __future__ import annotations

import argparse
import os
from ipaddress import IPv4Address
from urllib.parse import urlparse

import httpx

from app.shared.core.evidence_capture import sanitize_bearer_token

_ALL_INTERFACES_HOST = IPv4Address(0).compressed


def _normalize_base_url(raw: str) -> str:
    value = str(raw or "").strip()
    if not value:
        return ""
    lowered = value.lower()
    if lowered.startswith(("http://", "https://")):
        return value
    if lowered.startswith(("localhost", "127.0.0.1", _ALL_INTERFACES_HOST)):
        return f"http://{value}"
    return f"https://{value}"


def _require_valid_base_url(raw: str) -> str:
    normalized = _normalize_base_url(raw)
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit(
            f"Invalid --url '{raw}'. Provide a full http(s) URL like 'http://127.0.0.1:8000'."
        )
    return normalized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture carbon assurance evidence into audit logs."
    )
    parser.add_argument(
        "--url", default=os.environ.get("VALDRICS_API_URL", "http://127.0.0.1:8000")
    )
    parser.add_argument("--token", default=os.environ.get("VALDRICS_TOKEN"))
    parser.add_argument(
        "--runner", default="scripts/capture_carbon_assurance_evidence.py"
    )
    parser.add_argument("--notes", default=None)
    args = parser.parse_args(argv)

    raw_token = str(args.token or "").strip()
    try:
        token = sanitize_bearer_token(raw_token)
    except ValueError as exc:
        raise SystemExit(
            "Invalid token (VALDRICS_TOKEN/--token). "
            "Ensure it's a single JWT string. "
            f"Details: {exc}"
        ) from None
    if not token:
        raise SystemExit("Missing token. Set VALDRICS_TOKEN or pass --token.")

    url = _require_valid_base_url(str(args.url))
    endpoint = f"{url}/api/v1/audit/carbon/assurance/evidence"
    payload = {
        "runner": str(args.runner),
        "notes": (str(args.notes) if args.notes else None),
    }
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with httpx.Client(timeout=20.0, headers=headers) as client:
            resp = client.post(endpoint, json=payload)
    except httpx.RequestError as exc:
        raise SystemExit(
            "Capture failed while calling "
            f"{endpoint}. Ensure the API is reachable and --url/VALDRICS_API_URL is correct. "
            f"Underlying error: {exc.__class__.__name__}: {exc}"
        ) from exc
    if not resp.is_success:
        raise SystemExit(
            f"Capture failed: HTTP {resp.status_code} -> {resp.text[:300]}"
        )

    body = resp.json()
    print(
        f"[carbon] captured: event_id={body.get('event_id')} run_id={body.get('run_id')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
