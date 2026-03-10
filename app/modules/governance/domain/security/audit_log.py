"""
SOC2-Ready Audit Logging

Implements comprehensive audit logging for compliance with:
- SOC2 Type II (Security, Availability, Processing Integrity)
- GDPR Article 30 (Records of Processing Activities)
- ISO 27001 (Information Security Management)

Key Features:
1. Write-once audit trail with controlled retention purge
2. Structured events with correlation IDs
3. User action tracking with context
4. Sensitive data masking
5. Export capability for auditors
"""

import inspect
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Union, cast
from sqlalchemy import String, ForeignKey, Text, Index, JSON, Uuid, DateTime, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
import structlog

from app.models._encryption import get_encryption_key
from app.shared.db.base import Base, get_partition_args
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine

logger = structlog.get_logger()


class AuditEventType(str, Enum):
    """Categorized audit event types for filtering and reporting."""

    # Authentication
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_FAILED = "auth.failed"
    AUTH_MFA_ENABLED = "auth.mfa_enabled"

    # Resource Access
    RESOURCE_READ = "resource.read"
    RESOURCE_CREATE = "resource.create"
    RESOURCE_UPDATE = "resource.update"
    RESOURCE_DELETE = "resource.delete"

    # AWS Connection
    AWS_CONNECTED = "aws.connected"
    AWS_DISCONNECTED = "aws.disconnected"
    AWS_ROLE_ASSUMED = "aws.role_assumed"

    # Remediation
    REMEDIATION_REQUESTED = "remediation.requested"
    REMEDIATION_APPROVED = "remediation.approved"
    REMEDIATION_REJECTED = "remediation.rejected"
    REMEDIATION_EXECUTION_STARTED = "remediation.execution_started"
    REMEDIATION_EXECUTED = "remediation.executed"
    REMEDIATION_FAILED = "remediation.failed"
    POLICY_EVALUATED = "policy.evaluated"
    POLICY_WARNED = "policy.warned"
    POLICY_BLOCKED = "policy.blocked"
    POLICY_ESCALATED = "policy.escalated"

    # Optimization
    OPTIMIZATION_RECOMMENDATION_APPLIED = "optimization.recommendation_applied"

    # Attribution / Chargeback
    ATTRIBUTION_RULE_CREATED = "attribution.rule_created"
    ATTRIBUTION_RULE_UPDATED = "attribution.rule_updated"
    ATTRIBUTION_RULE_DELETED = "attribution.rule_deleted"
    ATTRIBUTION_RULE_SIMULATED = "attribution.rule_simulated"
    ATTRIBUTION_RULES_APPLIED = "attribution.rules_applied"

    # Tenants
    TENANT_CREATED = "tenant.created"
    TENANT_DELETED = "tenant.deleted"

    # Settings
    SETTINGS_UPDATED = "settings.updated"
    AUTO_PILOT_ENABLED = "settings.auto_pilot_enabled"
    AUTO_PILOT_DISABLED = "settings.auto_pilot_disabled"

    # SCIM provisioning
    SCIM_USER_CREATED = "scim.user_created"
    SCIM_USER_UPDATED = "scim.user_updated"
    SCIM_USER_DEPROVISIONED = "scim.user_deprovisioned"
    SCIM_TOKEN_ROTATED = "scim.token_rotated"  # nosec B105 - audit event identifier
    SCIM_GROUP_CREATED = "scim.group_created"
    SCIM_GROUP_UPDATED = "scim.group_updated"
    SCIM_GROUP_DELETED = "scim.group_deleted"
    SECURITY_EMERGENCY_TOKEN_ISSUED = (
        "security.emergency_token_issued"  # nosec B105 - audit event identifier
    )

    # Identity (tenant-scoped enforcement primitives)
    IDENTITY_SETTINGS_UPDATED = "identity.settings_updated"
    IDENTITY_IDP_SMOKE_CAPTURED = "identity.idp_smoke_captured"
    IDENTITY_SSO_FEDERATION_VALIDATION_CAPTURED = (
        "identity.sso_federation_validation_captured"
    )

    # Billing
    BILLING_SUBSCRIPTION_CREATED = "billing.subscription_created"
    BILLING_PAYMENT_INITIATED = "billing.payment_initiated"
    BILLING_PAYMENT_RECEIVED = "billing.payment_received"
    BILLING_PAYMENT_FAILED = "billing.payment_failed"

    # Budget hard-cap enforcement
    BUDGET_HARD_CAP_ENFORCEMENT_BLOCKED = "budget.hard_cap_enforcement_blocked"
    BUDGET_HARD_CAP_ENFORCED = "budget.hard_cap_enforced"
    BUDGET_HARD_CAP_REVERSED = "budget.hard_cap_reversed"

    # Integration acceptance evidence
    INTEGRATION_TEST_SLACK = "integration_test.slack"
    INTEGRATION_TEST_JIRA = "integration_test.jira"
    INTEGRATION_TEST_TEAMS = "integration_test.teams"
    INTEGRATION_TEST_WORKFLOW = "integration_test.workflow"
    INTEGRATION_TEST_TENANCY = "integration_test.tenancy"
    INTEGRATION_TEST_SUITE = "integration_test.suite"

    # Acceptance evidence snapshots
    ACCEPTANCE_KPIS_CAPTURED = "acceptance.kpis_captured"
    ACCEPTANCE_CLOSE_PACKAGE_CAPTURED = "acceptance.close_package_captured"
    PERFORMANCE_LOAD_TEST_CAPTURED = "performance.load_test_captured"
    PERFORMANCE_INGESTION_PERSISTENCE_CAPTURED = (
        "performance.ingestion_persistence_captured"
    )
    PERFORMANCE_INGESTION_SOAK_CAPTURED = "performance.ingestion_soak_captured"
    PERFORMANCE_PARTITIONING_CAPTURED = "performance.partitioning_captured"
    JOBS_SLO_CAPTURED = "jobs.slo_captured"
    TENANCY_ISOLATION_VERIFICATION_CAPTURED = "tenancy.isolation_verification_captured"
    CARBON_ASSURANCE_SNAPSHOT_CAPTURED = "carbon.assurance_snapshot_captured"

    # Leadership / commercial proof evidence
    LEADERSHIP_KPIS_CAPTURED = "leadership.kpis_captured"
    COMMERCIAL_QUARTERLY_REPORT_CAPTURED = "commercial.quarterly_report_captured"

    # Enterprise close / invoice reconciliation
    INVOICE_UPSERTED = "invoice.upserted"
    INVOICE_DELETED = "invoice.deleted"
    INVOICE_STATUS_UPDATED = "invoice.status_updated"

    # System
    SYSTEM_ERROR = "system.error"
    SYSTEM_MAINTENANCE = "system.maintenance"
    EXPORT_REQUESTED = "audit.export_requested"


class AuditLog(Base):
    """
    Write-once audit log entry for SOC2 compliance.

    Design Principles:
    - UPDATE is always forbidden
    - DELETE is reserved for the controlled retention purge path
    - Sensitive data masked before storage
    - Correlation ID links related events
    - Indexed for efficient querying by auditors
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Event classification
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        primary_key=True,  # Part of Partition Key
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        index=True,
    )

    # Actor information
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
        nullable=True,  # Null for system actions
        index=True,
    )
    actor_email: Mapped[Optional[str]] = mapped_column(
        StringEncryptedType(String(255), get_encryption_key, AesEngine, "pkcs5"),
        nullable=True,
    )
    actor_ip: Mapped[Optional[str]] = mapped_column(
        String(45), nullable=True
    )  # IPv6 max

    # Request context
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )
    request_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    request_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Resource affected
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Event details (JSONB for flexibility)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )

    # Outcome
    success: Mapped[bool] = mapped_column(default=True, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    tenant = relationship("Tenant")
    actor = relationship("User")

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_audit_tenant_time", "tenant_id", "event_timestamp"),
        Index("ix_audit_type_time", "event_type", "event_timestamp"),
        get_partition_args("RANGE (event_timestamp)"),
    )


class SystemAuditLog(Base):
    """
    Immutable system-scope audit log for events that cannot be attributed to a tenant.

    Design Principles:
    - Write-only via explicit system DB context
    - No tenant foreign key to avoid fabricating tenant ownership
    - Same masking and correlation semantics as tenant audit logs
    """

    __tablename__ = "system_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    actor_email: Mapped[Optional[str]] = mapped_column(
        StringEncryptedType(String(255), get_encryption_key, AesEngine, "pkcs5"),
        nullable=True,
    )
    actor_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )
    request_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    request_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    success: Mapped[bool] = mapped_column(default=True, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    actor = relationship("User")

    __table_args__ = (
        Index(
            "ix_system_audit_type_time",
            "event_type",
            "event_timestamp",
        ),
    )


def _coerce_actor_id(actor_id: uuid.UUID | str | None) -> uuid.UUID | None:
    if isinstance(actor_id, uuid.UUID):
        return actor_id
    if isinstance(actor_id, (str, bytes)):
        try:
            return uuid.UUID(str(actor_id))
        except ValueError:
            return None
    return None


class _AuditLoggerBase:
    # Fields to mask in details
    SENSITIVE_FIELDS = {
        "password",
        "token",
        "secret",
        "api_key",
        "access_key",
        "external_id",
        "session_token",
        "credit_card",
    }

    @classmethod
    def _mask_sensitive(cls, data: Any) -> Any:
        """
        Recursively mask sensitive fields in dicts and lists.
        Item 17: Extended to handle nested JSONB and list structures.
        """
        if isinstance(data, list):
            return [cls._mask_sensitive(item) for item in data]

        if not isinstance(data, dict):
            return data

        masked = {}
        for key, value in data.items():
            if any(
                sensitive in str(key).lower() for sensitive in cls.SENSITIVE_FIELDS
            ):
                masked[key] = "***REDACTED***"
            elif isinstance(value, (dict, list)):
                masked[key] = cls._mask_sensitive(value)
            else:
                masked[key] = value

        return masked


class AuditLogger(_AuditLoggerBase):
    """
    High-level audit logging service.

    Usage:
        audit = AuditLogger(db, tenant_id)
        await audit.log(
            event_type=AuditEventType.REMEDIATION_EXECUTED,
            actor_id=user.id,
            resource_type="EBS_VOLUME",
            resource_id="vol-123",
            details={"action": "delete", "savings": 50.00}
        )
    """

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: Union[str, uuid.UUID],
        correlation_id: str | None = None,
    ) -> None:
        self.db = db
        # Ensure tenant_id is a UUID object for SQLAlchemy
        self.tenant_id = (
            uuid.UUID(str(tenant_id))
            if isinstance(tenant_id, (str, bytes))
            else tenant_id
        )
        self.correlation_id = correlation_id or str(uuid.uuid4())

    async def log(
        self,
        event_type: AuditEventType | str,
        actor_id: uuid.UUID | str | None = None,
        actor_email: str | None = None,
        actor_ip: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        success: bool = True,
        error_message: str | None = None,
        request_method: str | None = None,
        request_path: str | None = None,
    ) -> AuditLog:
        """Create an immutable audit log entry."""

        # Mask sensitive data
        masked_details = self._mask_sensitive(details) if details else None
        parsed_actor_id = _coerce_actor_id(actor_id)

        entry = AuditLog(
            tenant_id=self.tenant_id,
            event_type=(
                event_type.value if isinstance(event_type, AuditEventType) else str(event_type)
            ),
            actor_id=parsed_actor_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            correlation_id=self.correlation_id,
            request_method=request_method,
            request_path=request_path,
            resource_type=resource_type,
            resource_id=resource_id,
            details=masked_details,
            success=success,
            error_message=error_message,
        )

        add_result = cast(Any, self.db).add(entry)
        # AsyncSession.add is sync, but AsyncMock-based tests may return awaitables.
        if inspect.isawaitable(add_result):
            await add_result
        await self.db.flush()

        # Also log to structured logger for real-time monitoring
        logger.info(
            "audit_event",
            event_type=(
                event_type.value if isinstance(event_type, AuditEventType) else str(event_type)
            ),
            tenant_id=str(self.tenant_id),
            correlation_id=self.correlation_id,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
        )

        return entry


class SystemAuditLogger(_AuditLoggerBase):
    """High-level audit logging service for system-scope events."""

    def __init__(
        self,
        db: AsyncSession,
        correlation_id: str | None = None,
    ) -> None:
        self.db = db
        self.correlation_id = correlation_id or str(uuid.uuid4())

    async def log(
        self,
        event_type: AuditEventType | str,
        actor_id: uuid.UUID | str | None = None,
        actor_email: str | None = None,
        actor_ip: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        success: bool = True,
        error_message: str | None = None,
        request_method: str | None = None,
        request_path: str | None = None,
    ) -> SystemAuditLog:
        masked_details = self._mask_sensitive(details) if details else None
        parsed_actor_id = _coerce_actor_id(actor_id)

        entry = SystemAuditLog(
            event_type=(
                event_type.value if isinstance(event_type, AuditEventType) else str(event_type)
            ),
            actor_id=parsed_actor_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            correlation_id=self.correlation_id,
            request_method=request_method,
            request_path=request_path,
            resource_type=resource_type,
            resource_id=resource_id,
            details=masked_details,
            success=success,
            error_message=error_message,
        )

        add_result = cast(Any, self.db).add(entry)
        if inspect.isawaitable(add_result):
            await add_result
        await self.db.flush()

        logger.info(
            "system_audit_event",
            event_type=(
                event_type.value if isinstance(event_type, AuditEventType) else str(event_type)
            ),
            correlation_id=self.correlation_id,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
        )

        return entry


@event.listens_for(AuditLog, "before_update")
def _audit_log_prevent_update(*_: object) -> None:
    raise ValueError("AuditLog entries are immutable once written.")


@event.listens_for(AuditLog, "before_delete")
def _audit_log_prevent_delete(*_: object) -> None:
    raise ValueError(
        "AuditLog entries can only be deleted by the controlled retention purge path."
    )


@event.listens_for(SystemAuditLog, "before_update")
def _system_audit_log_prevent_update(*_: object) -> None:
    raise ValueError("SystemAuditLog entries are immutable once written.")


@event.listens_for(SystemAuditLog, "before_delete")
def _system_audit_log_prevent_delete(*_: object) -> None:
    raise ValueError("SystemAuditLog entries cannot be deleted directly.")
