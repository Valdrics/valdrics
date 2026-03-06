from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


_POLICY_DOCUMENT_SCHEMA_VERSION = "valdrics.enforcement.policy.v1"
_EMPTY_POLICY_DOCUMENT_SHA256 = "0" * 64


class EnforcementSource(str, Enum):
    TERRAFORM = "terraform"
    K8S_ADMISSION = "k8s_admission"
    CLOUD_EVENT = "cloud_event"


class EnforcementMode(str, Enum):
    SHADOW = "shadow"
    SOFT = "soft"
    HARD = "hard"


class EnforcementDecisionType(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    ALLOW_WITH_CREDITS = "ALLOW_WITH_CREDITS"


class EnforcementCreditPoolType(str, Enum):
    RESERVED = "reserved"
    EMERGENCY = "emergency"


class EnforcementApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class EnforcementActionStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


__all__ = [
    "_utcnow",
    "_POLICY_DOCUMENT_SCHEMA_VERSION",
    "_EMPTY_POLICY_DOCUMENT_SHA256",
    "EnforcementSource",
    "EnforcementMode",
    "EnforcementDecisionType",
    "EnforcementCreditPoolType",
    "EnforcementApprovalStatus",
    "EnforcementActionStatus",
]
