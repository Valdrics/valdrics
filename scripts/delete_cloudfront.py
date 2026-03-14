from __future__ import annotations

import argparse
import sys
import time

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from scripts.safety_guardrails import (
    current_environment,
    ensure_environment_confirmation,
    ensure_force_and_phrase,
    ensure_interactive_confirmation,
    ensure_operator_reason,
    ensure_protected_environment_bypass,
)

CONFIRM_PHRASE = (
    "DELETE_CLOUDFRONT_DISTRIBUTION"
    # nosec B105 - explicit operator confirmation phrase
)
INTERACTIVE_CONFIRM_TOKEN = (
    "DELETE_CLOUDFRONT"
    # nosec B105 - explicit interactive confirmation token
)
PROD_BYPASS = (
    "I_UNDERSTAND_CLOUDFRONT_DELETE_RISK"
    # nosec B105 - explicit protected-environment bypass phrase
)
NONINTERACTIVE_BYPASS_ENV = "VALDRICS_ALLOW_NONINTERACTIVE_CLOUDFRONT_DELETE"
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
        bypass_env_var="VALDRICS_ALLOW_PROD_CLOUDFRONT_DELETE",
        bypass_phrase=PROD_BYPASS,
        operation_label="CloudFront delete",
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
        operation_label="CloudFront delete",
    )


def delete_cloudfront(*, distribution_id: str, dry_run: bool) -> bool:
    distribution = str(distribution_id or "").strip()
    if not distribution:
        raise RuntimeError("distribution_id is required")
    if dry_run:
        print(f"Dry-run: would delete CloudFront distribution {distribution}.")
        return True

    client = boto3.client("cloudfront")
    print(f"Waiting for distribution {distribution} to be fully disabled...")

    while True:
        try:
            response = client.get_distribution_config(Id=distribution)
            config = response["DistributionConfig"]
            etag = response["ETag"]

            dist_response = client.get_distribution(Id=distribution)
            status = dist_response["Distribution"]["Status"]

            if config["Enabled"]:
                print("Distribution is still enabled. Disabling...")
                config["Enabled"] = False
                client.update_distribution(
                    Id=distribution,
                    IfMatch=etag,
                    DistributionConfig=config,
                )
                time.sleep(5)
                continue

            if status != "Deployed":
                print(f"Distribution status is '{status}'. Waiting for 'Deployed'...")
                time.sleep(15)
                continue

            print("Distribution is disabled and deployed. Attempting deletion...")
            client.delete_distribution(Id=distribution, IfMatch=etag)
            print(f"Successfully deleted {distribution}.")
            return True

        except ClientError as exc:
            error_code = str(exc.response.get("Error", {}).get("Code") or "").strip()
            if error_code == "DistributionNotDisabled":
                print("AWS reports distribution not disabled yet. Retrying...")
                time.sleep(10)
                continue
            if error_code == "InvalidIfMatchVersion":
                print("ETag mismatch, retrying...")
                continue
            print(f"ClientError: {exc}", file=sys.stderr)
            return False
        except (BotoCoreError, OSError, RuntimeError, TypeError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run by default. Delete a CloudFront distribution only with explicit confirmation."
    )
    parser.add_argument(
        "--distribution-id",
        required=True,
        help="CloudFront distribution ID to delete.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform the delete. Without this flag the script only reports impact.",
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
        success = delete_cloudfront(
            distribution_id=str(args.distribution_id),
            dry_run=not bool(args.execute),
        )
    except RuntimeError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
