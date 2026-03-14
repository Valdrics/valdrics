from __future__ import annotations

import argparse
import sys

import boto3
from botocore.exceptions import BotoCoreError

from scripts.safety_guardrails import (
    current_environment,
    ensure_environment_confirmation,
    ensure_force_and_phrase,
    ensure_interactive_confirmation,
    ensure_operator_reason,
    ensure_protected_environment_bypass,
)

CONFIRM_PHRASE = (
    "DISABLE_CLOUDFRONT_DISTRIBUTION"
    # nosec B105 - explicit operator confirmation phrase
)
INTERACTIVE_CONFIRM_TOKEN = (
    "DISABLE_CLOUDFRONT"
    # nosec B105 - explicit interactive confirmation token
)
PROD_BYPASS = (
    "I_UNDERSTAND_CLOUDFRONT_DISABLE_RISK"
    # nosec B105 - explicit protected-environment bypass phrase
)
NONINTERACTIVE_BYPASS_ENV = "VALDRICS_ALLOW_NONINTERACTIVE_CLOUDFRONT_DISABLE"
MIN_REASON_LENGTH = 16


def _validate_request(
    *,
    force: bool,
    phrase: str,
    confirm_environment: str,
    no_prompt: bool,
    operator: str,
    reason: str,
) -> None:
    environment = current_environment()
    ensure_protected_environment_bypass(
        environment=environment,
        bypass_env_var="VALDRICS_ALLOW_PROD_CLOUDFRONT_DISABLE",
        bypass_phrase=PROD_BYPASS,
        operation_label="CloudFront disable",
    )
    ensure_force_and_phrase(force=force, phrase=phrase, expected_phrase=CONFIRM_PHRASE)
    ensure_environment_confirmation(
        confirm_environment=confirm_environment,
        environment=environment,
    )
    ensure_interactive_confirmation(
        token=INTERACTIVE_CONFIRM_TOKEN,
        no_prompt=no_prompt,
        noninteractive_env_var=NONINTERACTIVE_BYPASS_ENV,
    )
    ensure_operator_reason(
        operator=operator,
        reason=reason,
        min_reason_length=MIN_REASON_LENGTH,
        operation_label="CloudFront disable",
    )


def disable_cloudfront(*, distribution_id: str, dry_run: bool) -> bool:
    distribution = str(distribution_id or "").strip()
    if not distribution:
        raise RuntimeError("distribution_id is required")
    if dry_run:
        print(f"Dry-run: would disable CloudFront distribution {distribution}.")
        return True

    client = boto3.client("cloudfront")
    try:
        response = client.get_distribution_config(Id=distribution)
        etag = response["ETag"]
        config = response["DistributionConfig"]

        if not config["Enabled"]:
            print(f"Distribution {distribution} is already disabled.")
            return True

        print(f"Disabling distribution {distribution}...")
        config["Enabled"] = False

        client.update_distribution(
            Id=distribution,
            IfMatch=etag,
            DistributionConfig=config,
        )
        print(f"Successfully disabled {distribution}.")
        return True

    except (BotoCoreError, OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run by default. Disable a CloudFront distribution only with explicit confirmation."
    )
    parser.add_argument(
        "--distribution-id",
        required=True,
        help="CloudFront distribution ID to disable.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform the disable. Without this flag the script only reports impact.",
    )
    parser.add_argument("--operator", default="", help="Operator identifier (email or handle).")
    parser.add_argument(
        "--reason",
        default="",
        help=f"Break-glass reason (minimum {MIN_REASON_LENGTH} characters).",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--confirm-phrase", default="")
    parser.add_argument("--confirm-environment", default="")
    parser.add_argument("--no-prompt", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.execute:
            _validate_request(
                force=bool(args.force),
                phrase=str(args.confirm_phrase),
                confirm_environment=str(args.confirm_environment),
                no_prompt=bool(args.no_prompt),
                operator=str(args.operator),
                reason=str(args.reason),
            )
        success = disable_cloudfront(
            distribution_id=str(args.distribution_id),
            dry_run=not bool(args.execute),
        )
    except RuntimeError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
