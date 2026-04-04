from __future__ import annotations

import base64
import json
from uuid import uuid4

import pytest

from tests.unit.enforcement.enforcement_service_cases_common import (
    HTTPException,
    EnforcementService,
    _issue_approved_token,
    _seed_tenant,
)


@pytest.mark.asyncio
async def test_consume_approval_token_endpoint_rejects_replay_and_tamper(db) -> None:
    tenant = await _seed_tenant(db)
    tenant_id = tenant.id
    actor_id = uuid4()
    token, _, _ = await _issue_approved_token(
        db=db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        idempotency_key="drill-selector-replay-tamper-1",
    )

    service = EnforcementService(db)
    consumed_approval, consumed_decision = await service.consume_approval_token(
        tenant_id=tenant_id,
        approval_token=token,
        actor_id=actor_id,
    )
    assert consumed_approval.approval_token_consumed_at is not None
    assert consumed_decision.request_fingerprint

    with pytest.raises(HTTPException) as replay_exc:
        await service.consume_approval_token(
            tenant_id=tenant_id,
            approval_token=token,
            actor_id=actor_id,
        )
    assert replay_exc.value.status_code == 409
    assert "replay" in str(replay_exc.value.detail).lower()

    header, payload, signature = token.split(".")
    decoded_payload = json.loads(base64.urlsafe_b64decode(payload + "==").decode())
    decoded_payload["resource_reference"] = "module.hijack.aws_iam_role.admin"
    tampered_payload = (
        base64.urlsafe_b64encode(json.dumps(decoded_payload).encode())
        .decode()
        .rstrip("=")
    )
    tampered_token = f"{header}.{tampered_payload}.{signature}"

    with pytest.raises(HTTPException) as tamper_exc:
        await service.consume_approval_token(
            tenant_id=tenant_id,
            approval_token=tampered_token,
            actor_id=actor_id,
        )
    assert tamper_exc.value.status_code == 401
    assert "invalid approval token" in str(tamper_exc.value.detail).lower()
