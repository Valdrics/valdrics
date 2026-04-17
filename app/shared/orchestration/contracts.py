from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class PlatformRuntimeProfile(str, Enum):
    GCP = "gcp"


class ObservabilityBackend(str, Enum):
    GCP = "gcp"


class WorkExecutionMode(str, Enum):
    TASK = "task"
    BATCH = "batch"


class ManagedWorkItem(str, Enum):
    BACKGROUND_JOB_PROCESSING = "background_jobs.process"
    BACKGROUND_JOB_STUCK_DETECTION = "background_jobs.detect_stuck"
    SCHEDULER_COHORT_ANALYSIS = "scheduler.cohort_analysis"
    SCHEDULER_REMEDIATION_SWEEP = "scheduler.remediation_sweep"
    SCHEDULER_BILLING_SWEEP = "scheduler.billing_sweep"
    SCHEDULER_ACCEPTANCE_SWEEP = "scheduler.acceptance_sweep"
    LICENSE_GOVERNANCE_SWEEP = "license.governance_sweep"
    SCHEDULER_ENFORCEMENT_RECONCILIATION_SWEEP = (
        "scheduler.enforcement_reconciliation_sweep"
    )
    SCHEDULER_MAINTENANCE_SWEEP = "scheduler.maintenance_sweep"
    SCHEDULER_LANDING_FUNNEL_HEALTH_REFRESH = "scheduler.refresh_landing_funnel_health"


class DispatchUnavailableError(RuntimeError):
    """Raised when the configured transport cannot accept work."""


@dataclass(frozen=True)
class ManagedWorkSpec:
    work_item: ManagedWorkItem
    execution_mode: WorkExecutionMode
    description: str


WORK_SPECS: dict[ManagedWorkItem, ManagedWorkSpec] = {
    ManagedWorkItem.BACKGROUND_JOB_PROCESSING: ManagedWorkSpec(
        work_item=ManagedWorkItem.BACKGROUND_JOB_PROCESSING,
        execution_mode=WorkExecutionMode.TASK,
        description="Drain durable background jobs.",
    ),
    ManagedWorkItem.BACKGROUND_JOB_STUCK_DETECTION: ManagedWorkSpec(
        work_item=ManagedWorkItem.BACKGROUND_JOB_STUCK_DETECTION,
        execution_mode=WorkExecutionMode.TASK,
        description="Detect overdue pending jobs and refresh stuck-job metrics.",
    ),
    ManagedWorkItem.SCHEDULER_COHORT_ANALYSIS: ManagedWorkSpec(
        work_item=ManagedWorkItem.SCHEDULER_COHORT_ANALYSIS,
        execution_mode=WorkExecutionMode.BATCH,
        description="Run cohort analysis sweep.",
    ),
    ManagedWorkItem.SCHEDULER_REMEDIATION_SWEEP: ManagedWorkSpec(
        work_item=ManagedWorkItem.SCHEDULER_REMEDIATION_SWEEP,
        execution_mode=WorkExecutionMode.BATCH,
        description="Run remediation sweep.",
    ),
    ManagedWorkItem.SCHEDULER_BILLING_SWEEP: ManagedWorkSpec(
        work_item=ManagedWorkItem.SCHEDULER_BILLING_SWEEP,
        execution_mode=WorkExecutionMode.BATCH,
        description="Run billing sweep.",
    ),
    ManagedWorkItem.SCHEDULER_ACCEPTANCE_SWEEP: ManagedWorkSpec(
        work_item=ManagedWorkItem.SCHEDULER_ACCEPTANCE_SWEEP,
        execution_mode=WorkExecutionMode.BATCH,
        description="Run acceptance evidence sweep.",
    ),
    ManagedWorkItem.LICENSE_GOVERNANCE_SWEEP: ManagedWorkSpec(
        work_item=ManagedWorkItem.LICENSE_GOVERNANCE_SWEEP,
        execution_mode=WorkExecutionMode.BATCH,
        description="Run license governance sweep.",
    ),
    ManagedWorkItem.SCHEDULER_ENFORCEMENT_RECONCILIATION_SWEEP: ManagedWorkSpec(
        work_item=ManagedWorkItem.SCHEDULER_ENFORCEMENT_RECONCILIATION_SWEEP,
        execution_mode=WorkExecutionMode.BATCH,
        description="Run enforcement reconciliation sweep.",
    ),
    ManagedWorkItem.SCHEDULER_MAINTENANCE_SWEEP: ManagedWorkSpec(
        work_item=ManagedWorkItem.SCHEDULER_MAINTENANCE_SWEEP,
        execution_mode=WorkExecutionMode.BATCH,
        description="Run maintenance sweep.",
    ),
    ManagedWorkItem.SCHEDULER_LANDING_FUNNEL_HEALTH_REFRESH: ManagedWorkSpec(
        work_item=ManagedWorkItem.SCHEDULER_LANDING_FUNNEL_HEALTH_REFRESH,
        execution_mode=WorkExecutionMode.TASK,
        description="Refresh landing funnel health telemetry.",
    ),
}


def get_work_spec(work_item: ManagedWorkItem) -> ManagedWorkSpec:
    return WORK_SPECS[work_item]


def platform_runtime_profile(settings_obj: object) -> PlatformRuntimeProfile:
    raw_value = (
        str(
            getattr(
                settings_obj,
                "PLATFORM_RUNTIME_PROFILE",
                PlatformRuntimeProfile.GCP.value,
            )
            or PlatformRuntimeProfile.GCP.value
        )
        .strip()
        .lower()
    )
    return PlatformRuntimeProfile(raw_value)


def observability_backend(settings_obj: object) -> ObservabilityBackend:
    raw_value = (
        str(
            getattr(
                settings_obj,
                "OBSERVABILITY_BACKEND",
                ObservabilityBackend.GCP.value,
            )
            or ObservabilityBackend.GCP.value
        )
        .strip()
        .lower()
    )
    selected = ObservabilityBackend(raw_value)
    if platform_runtime_profile(settings_obj) is not PlatformRuntimeProfile.GCP:
        raise ValueError(
            "Only the managed GCP runtime profile is supported for observability."
        )
    return selected


@dataclass(frozen=True)
class ManagedWorkRequest:
    work_item: ManagedWorkItem
    payload: dict[str, Any] = field(default_factory=dict)
    deduplication_key: str | None = None
    delay_seconds: int | None = None


@dataclass(frozen=True)
class ManagedWorkResult:
    accepted: bool
    transport: str
    reference: str | None = None


class AsyncTaskDispatcher(Protocol):
    async def dispatch(self, request: ManagedWorkRequest) -> ManagedWorkResult: ...


class ScheduledTriggerDispatcher(Protocol):
    async def dispatch(self, request: ManagedWorkRequest) -> ManagedWorkResult: ...


class BatchJobLauncher(Protocol):
    async def launch(self, request: ManagedWorkRequest) -> ManagedWorkResult: ...
