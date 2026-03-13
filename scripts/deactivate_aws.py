#!/usr/bin/env python3
"""Guarded bulk deactivation of AWS connections."""

from __future__ import annotations

import argparse
import asyncio
import sys

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.models.aws_connection import AWSConnection
from app.shared.db.session import async_session_maker
from scripts.safety_guardrails import (
    current_environment,
    ensure_environment_confirmation,
    ensure_force_and_phrase,
    ensure_interactive_confirmation,
    ensure_operator_reason,
    ensure_protected_environment_bypass,
)

logger = structlog.get_logger()

CONFIRM_PHRASE = (
    "DEACTIVATE_ALL_AWS_CONNECTIONS"  # nosec B105 - explicit operator confirmation phrase
)
INTERACTIVE_CONFIRM_TOKEN = (
    "DEACTIVATE_AWS_CONNECTIONS"  # nosec B105 - explicit interactive confirmation token
)
PROD_BYPASS = (
    "I_UNDERSTAND_AWS_CONNECTION_DEACTIVATION_RISK"
    # nosec B105 - explicit protected-environment bypass phrase
)
NONINTERACTIVE_BYPASS_ENV = "VALDRICS_ALLOW_NONINTERACTIVE_AWS_DEACTIVATION"
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
        bypass_env_var="VALDRICS_ALLOW_PROD_AWS_DEACTIVATION",
        bypass_phrase=PROD_BYPASS,
        operation_label="AWS connection deactivation",
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
        operation_label="AWS connection deactivation",
    )


async def deactivate_all_connections(
    *,
    dry_run: bool,
    operator: str,
    reason: str,
) -> int:
    async with async_session_maker() as session:
        active_count = int(
            (await session.execute(
                select(func.count()).select_from(AWSConnection).where(
                    AWSConnection.status != "inactive"
                )
            )).scalar_one()
            or 0
        )

        logger.info(
            "aws_connection_deactivation_requested",
            dry_run=dry_run,
            active_connections=active_count,
            operator=operator.strip(),
            reason=reason.strip(),
        )

        if dry_run:
            print(f"Dry-run: would deactivate {active_count} AWS connections.")
            return active_count

        try:
            result = await session.execute(
                update(AWSConnection)
                .where(AWSConnection.status != "inactive")
                .values(status="inactive")
            )
            await session.commit()
        except (SQLAlchemyError, OSError, RuntimeError, TypeError, ValueError) as exc:
            await session.rollback()
            logger.error(
                "aws_connection_deactivation_failed",
                error=str(exc),
                operator=operator.strip(),
                reason=reason.strip(),
            )
            raise

    affected = int(result.rowcount or 0)
    logger.info(
        "aws_connection_deactivation_complete",
        connections_affected=affected,
        operator=operator.strip(),
        reason=reason.strip(),
    )
    print(f"Successfully deactivated {affected} AWS connections.")
    return affected


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run by default. Use explicit break-glass confirmation to deactivate all AWS connections."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform the deactivation. Without this flag the script only reports impact.",
    )
    parser.add_argument("--operator", default="", help="Operator identifier (email or handle).")
    parser.add_argument(
        "--reason",
        default="",
        help=f"Break-glass reason (minimum {MIN_REASON_LENGTH} characters).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Acknowledge destructive operation.",
    )
    parser.add_argument(
        "--confirm-phrase",
        default="",
        help=f"Must equal {CONFIRM_PHRASE!r} to execute.",
    )
    parser.add_argument(
        "--confirm-environment",
        default="",
        help="Must match current ENVIRONMENT exactly (normalized to lowercase).",
    )
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help=(
            "Skip interactive typed confirmation. Requires "
            f"{NONINTERACTIVE_BYPASS_ENV}=true."
        ),
    )
    args = parser.parse_args()

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
        asyncio.run(
            deactivate_all_connections(
                dry_run=not bool(args.execute),
                operator=str(args.operator),
                reason=str(args.reason),
            )
        )
    except RuntimeError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError, TypeError, ValueError, SQLAlchemyError) as exc:
        print(f"❌ Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
