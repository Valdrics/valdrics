#!/usr/bin/env python3
"""Guarded emergency disconnect for a single AWS connection.

This script only performs the Valdrics-side disconnect. Any AWS-side trust or
policy revocation must be completed manually under the documented incident
response runbook.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from uuid import UUID

import structlog
from sqlalchemy.exc import SQLAlchemyError

from app.models.aws_connection import AWSConnection
from app.modules.governance.domain.security.audit_log import AuditEventType, AuditLogger
from app.shared.db.session import async_session_maker, mark_session_system_context
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
    "EMERGENCY_DISCONNECT_AWS_CONNECTION"
    # nosec B105 - explicit operator confirmation phrase
)
INTERACTIVE_CONFIRM_TOKEN = (
    "DISCONNECT_AWS_CONNECTION"
    # nosec B105 - explicit interactive confirmation token
)
PROD_BYPASS = (
    "I_UNDERSTAND_EMERGENCY_DISCONNECT_RISK"
    # nosec B105 - explicit protected-environment bypass phrase
)
NONINTERACTIVE_BYPASS_ENV = "VALDRICS_ALLOW_NONINTERACTIVE_EMERGENCY_DISCONNECT"
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
        bypass_env_var="VALDRICS_ALLOW_PROD_EMERGENCY_DISCONNECT",
        bypass_phrase=PROD_BYPASS,
        operation_label="emergency AWS disconnect",
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
        operation_label="emergency AWS disconnect",
    )


async def disconnect_connection(
    *,
    connection_id: str,
    dry_run: bool,
    operator: str,
    reason: str,
) -> dict[str, object]:
    target_id = UUID(str(connection_id).strip())

    async with async_session_maker() as session:
        await mark_session_system_context(session)
        connection = await session.get(AWSConnection, target_id)
        if connection is None:
            raise RuntimeError(f"AWS connection not found: {target_id}")

        payload: dict[str, object] = {
            "connection_id": str(connection.id),
            "tenant_id": str(connection.tenant_id),
            "aws_account_id": str(connection.aws_account_id),
            "previous_status": str(connection.status),
            "manual_aws_revocation_required": True,
        }

        logger.info(
            "emergency_disconnect_requested",
            dry_run=dry_run,
            operator=operator.strip(),
            reason=reason.strip(),
            **payload,
        )

        if dry_run:
            print(json.dumps({"mode": "dry_run", **payload}, sort_keys=True))
            return payload

        try:
            connection.status = "inactive"
            connection.error_message = f"Emergency disconnect: {reason.strip()}"
            audit = AuditLogger(
                db=session,
                tenant_id=connection.tenant_id,
                correlation_id=f"emergency-disconnect:{connection.id}",
            )
            await audit.log(
                event_type=AuditEventType.AWS_DISCONNECTED,
                actor_email=operator.strip(),
                resource_type="aws_connection",
                resource_id=str(connection.id),
                details={
                    "operator": operator.strip(),
                    "reason": reason.strip(),
                    "disconnect_mode": "app_side_only",
                    "aws_account_id": str(connection.aws_account_id),
                    "manual_aws_revocation_required": True,
                },
                success=True,
            )
            await session.commit()
        except (SQLAlchemyError, OSError, RuntimeError, TypeError, ValueError) as exc:
            await session.rollback()
            logger.error(
                "emergency_disconnect_failed",
                operator=operator.strip(),
                reason=reason.strip(),
                error=str(exc),
                **payload,
            )
            raise

    print(json.dumps({"mode": "executed", **payload}, sort_keys=True))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run by default. Use explicit break-glass confirmation to deactivate "
            "a single AWS connection inside Valdrics."
        )
    )
    parser.add_argument(
        "--connection-id",
        required=True,
        help="AWS connection UUID to deactivate.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform the disconnect. Without this flag the script only reports impact.",
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
            disconnect_connection(
                connection_id=str(args.connection_id),
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
