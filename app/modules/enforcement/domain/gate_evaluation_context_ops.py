from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from app.models.enforcement import EnforcementMode, EnforcementSource
from app.modules.enforcement.domain.gate_evaluation_persistence_ops import (
    resolve_idempotency_key,
)


@dataclass(frozen=True)
class GateEvaluationContext:
    policy: Any
    normalized_env: str
    mode: EnforcementMode
    mode_scope: str
    ttl_seconds: int
    fingerprint: str
    idempotency_key: str


async def build_gate_evaluation_context(
    *,
    service: Any,
    tenant_id: UUID,
    source: EnforcementSource,
    gate_input: Any,
    stable_fingerprint_fn: Callable[[EnforcementSource, Any], str],
    normalize_environment_fn: Callable[[str], str],
) -> GateEvaluationContext:
    policy = await service.get_or_create_policy(tenant_id)
    normalized_env = normalize_environment_fn(gate_input.environment)
    mode, mode_scope = service._resolve_policy_mode(
        policy=policy,
        source=source,
        environment=normalized_env,
    )
    ttl_seconds = max(60, min(int(policy.default_ttl_seconds), 86400))
    fingerprint = stable_fingerprint_fn(source, gate_input)
    idempotency_key = resolve_idempotency_key(
        fingerprint=fingerprint,
        idempotency_key=gate_input.idempotency_key,
    )
    return GateEvaluationContext(
        policy=policy,
        normalized_env=normalized_env,
        mode=mode,
        mode_scope=mode_scope,
        ttl_seconds=ttl_seconds,
        fingerprint=fingerprint,
        idempotency_key=idempotency_key,
    )

