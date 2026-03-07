"""
Capture acceptance evidence artifacts for operator sign-off.

This script is intentionally operator-safe:
- It never writes bearer tokens to disk.
- It redacts common secret keys from JSON artifacts.
- It produces a timestamped bundle under reports/acceptance/ (gitignored).
"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse

import httpx

from app.shared.core.evidence_capture import sanitize_bearer_token
from scripts.capture_acceptance_bootstrap import bootstrap_in_process_app_and_token
from scripts.capture_acceptance_runner import (
    CaptureResult,
    capture_acceptance_evidence as _capture_acceptance_evidence,
)


def _normalize_base_url(raw: str) -> str:
    """
    Normalize a base URL for httpx/urljoin.

    Operators frequently set VALDRICS_API_URL as `127.0.0.1:8000` without a scheme.
    We accept that and infer a scheme:
    - localhost/127.0.0.1/0.0.0.0 -> http
    - everything else -> https
    """
    value = str(raw or "").strip()
    if not value:
        return ""
    lowered = value.lower()
    if lowered.startswith(("http://", "https://")):
        return value
    if lowered.startswith(("localhost", "127.0.0.1", "0.0.0.0")):
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


def _iso_date(value: str) -> date:
    return date.fromisoformat(value)


def _default_start_end() -> tuple[date, date]:
    end = date.today()
    start = end - timedelta(days=30)
    return start, end


def _previous_full_month() -> tuple[date, date]:
    today = date.today()
    first_this_month = today.replace(day=1)
    prev_month_end = first_this_month - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    return prev_month_start, prev_month_end


async def capture_acceptance_evidence(
    *,
    base_url: str,
    token: str,
    output_root: Path,
    start_date: date,
    end_date: date,
    close_start_date: date,
    close_end_date: date,
    close_provider: str = "all",
    close_enforce_finalized: bool = False,
    timeout_seconds: float = 60.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[Path, list[CaptureResult]]:
    return await _capture_acceptance_evidence(
        base_url=base_url,
        token=token,
        output_root=output_root,
        start_date=start_date,
        end_date=end_date,
        close_start_date=close_start_date,
        close_end_date=close_end_date,
        close_provider=close_provider,
        close_enforce_finalized=close_enforce_finalized,
        timeout_seconds=timeout_seconds,
        transport=transport,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture Valdrics acceptance evidence artifacts."
    )
    parser.add_argument(
        "--url", default=os.environ.get("VALDRICS_API_URL", "http://127.0.0.1:8000")
    )
    parser.add_argument("--token", default=os.environ.get("VALDRICS_TOKEN"))
    parser.add_argument("--output-root", default="reports/acceptance")
    parser.add_argument(
        "--in-process",
        action="store_true",
        help="Run capture against an in-process app + sqlite DB (no live environment required).",
    )
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--close-start-date", default=None)
    parser.add_argument("--close-end-date", default=None)
    parser.add_argument("--close-provider", default="all")
    parser.add_argument("--close-enforce-finalized", action="store_true")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=60.0,
        help="HTTP timeout for each capture request.",
    )
    return parser


def _parse_window(
    *,
    start_date_raw: str | None,
    end_date_raw: str | None,
) -> tuple[date, date]:
    if start_date_raw and end_date_raw:
        try:
            return _iso_date(start_date_raw), _iso_date(end_date_raw)
        except ValueError as exc:
            raise SystemExit(f"Invalid date format for --start-date/--end-date: {exc}") from None
    return _default_start_end()


def _parse_close_window(
    *,
    close_start_date_raw: str | None,
    close_end_date_raw: str | None,
) -> tuple[date, date]:
    if close_start_date_raw and close_end_date_raw:
        try:
            return _iso_date(close_start_date_raw), _iso_date(close_end_date_raw)
        except ValueError as exc:
            raise SystemExit(
                f"Invalid date format for --close-start-date/--close-end-date: {exc}"
            ) from None
    return _previous_full_month()


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    transport: httpx.AsyncBaseTransport | None = None
    raw_url = str(args.url or "").strip()
    token = str(args.token or "").strip()

    if args.in_process:
        transport, token = asyncio.run(bootstrap_in_process_app_and_token())
        base_url = "http://test"
    else:
        if not raw_url:
            fallback = (
                os.environ.get("VALDRICS_API_URL", "").strip() or "http://127.0.0.1:8000"
            )
            print(f"[acceptance] warning: empty --url; defaulting to {fallback}")
            raw_url = fallback
        base_url = _require_valid_base_url(raw_url)

    try:
        token = sanitize_bearer_token(token)
    except ValueError as exc:
        raise SystemExit(
            "Invalid token (VALDRICS_TOKEN/--token). "
            "Ensure it's a single JWT string. "
            f"Details: {exc}"
        ) from None

    if not token:
        raise SystemExit(
            "Missing token. Set VALDRICS_TOKEN or pass --token (or use --in-process)."
        )

    start_date, end_date = _parse_window(
        start_date_raw=args.start_date,
        end_date_raw=args.end_date,
    )
    close_start_date, close_end_date = _parse_close_window(
        close_start_date_raw=args.close_start_date,
        close_end_date_raw=args.close_end_date,
    )

    if start_date > end_date:
        raise SystemExit("Invalid window: start_date must be <= end_date")
    if close_start_date > close_end_date:
        raise SystemExit(
            "Invalid close window: close_start_date must be <= close_end_date"
        )

    bundle_dir, results = asyncio.run(
        capture_acceptance_evidence(
            base_url=base_url,
            token=str(token).strip(),
            output_root=Path(args.output_root),
            start_date=start_date,
            end_date=end_date,
            close_start_date=close_start_date,
            close_end_date=close_end_date,
            close_provider=str(args.close_provider or "all"),
            close_enforce_finalized=bool(args.close_enforce_finalized),
            timeout_seconds=float(args.timeout_seconds),
            transport=transport,
        )
    )

    ok_count = sum(1 for result in results if result.ok)
    print(f"[acceptance] wrote bundle: {bundle_dir}")
    print(f"[acceptance] results: {ok_count}/{len(results)} ok")
    if ok_count == 0:
        print(
            "[acceptance] error: 0 captures succeeded. Check VALDRICS_API_URL/--url and VALDRICS_TOKEN."
        )
        print(f"[acceptance] details: {bundle_dir / 'manifest.json'}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
