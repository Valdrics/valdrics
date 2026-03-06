# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_api_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_reconcile_reservation_header_idempotency_key_precedence(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)

    try:
        gate_payload = await _create_pending_approval_via_api(
            async_client,
            idempotency_key="api-reconcile-reservation-idem-4",
            environment="nonprod",
            require_approval_for_prod=False,
            require_approval_for_nonprod=True,
        )
        decision_id = gate_payload["decision_id"]

        first = await async_client.post(
            f"/api/v1/enforcement/reservations/{decision_id}/reconcile",
            headers={"Idempotency-Key": "api-reconcile-header-idem-1"},
            json={
                "actual_monthly_delta_usd": "80",
                "notes": "header-precedence",
                "idempotency_key": "api-reconcile-body-shadow-a",
            },
        )
        assert first.status_code == 200
        first_body = first.json()

        replay = await async_client.post(
            f"/api/v1/enforcement/reservations/{decision_id}/reconcile",
            headers={"Idempotency-Key": "api-reconcile-header-idem-1"},
            json={
                "actual_monthly_delta_usd": "80",
                "notes": "header-precedence",
                "idempotency_key": "api-reconcile-body-shadow-b",
            },
        )
        assert replay.status_code == 200
        assert replay.json() == first_body
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_reconcile_overdue_endpoint_releases_stale_reservations(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)

    try:
        gate_payload = await _create_pending_approval_via_api(
            async_client,
            idempotency_key="api-reconcile-overdue-1",
            environment="nonprod",
            require_approval_for_prod=False,
            require_approval_for_nonprod=True,
        )
        decision_id = gate_payload["decision_id"]
        decision = (
            await db.execute(
                select(EnforcementDecision).where(
                    EnforcementDecision.id == UUID(decision_id)
                )
            )
        ).scalar_one()
        decision.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        await db.commit()

        reconcile = await async_client.post(
            "/api/v1/enforcement/reservations/reconcile-overdue",
            json={"older_than_seconds": 3600, "limit": 200},
        )
        assert reconcile.status_code == 200
        body = reconcile.json()
        assert body["released_count"] == 1
        assert body["total_released_usd"] == "75.0000"
        assert decision_id in body["decision_ids"]
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_reconcile_reservation_endpoint_forbids_member(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)

    try:
        gate_payload = await _create_pending_approval_via_api(
            async_client,
            idempotency_key="api-reconcile-member-denied-1",
            environment="nonprod",
            require_approval_for_prod=False,
            require_approval_for_nonprod=True,
        )
        decision_id = gate_payload["decision_id"]

        member_user = CurrentUser(
            id=uuid4(),
            email="member@enforcement.local",
            tenant_id=tenant.id,
            role=UserRole.MEMBER,
        )
        _override_user(async_client, member_user)

        reconcile = await async_client.post(
            f"/api/v1/enforcement/reservations/{decision_id}/reconcile",
            json={"actual_monthly_delta_usd": "80"},
        )
        assert reconcile.status_code == 403
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_reconciliation_exceptions_endpoint_returns_drift_only(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)

    try:
        drift_payload = await _create_pending_approval_via_api(
            async_client,
            idempotency_key="api-reconcile-exception-drift-1",
            environment="nonprod",
            require_approval_for_prod=False,
            require_approval_for_nonprod=True,
        )
        matched_payload = await _create_pending_approval_via_api(
            async_client,
            idempotency_key="api-reconcile-exception-matched-1",
            environment="nonprod",
            require_approval_for_prod=False,
            require_approval_for_nonprod=True,
        )

        drift_id = drift_payload["decision_id"]
        matched_id = matched_payload["decision_id"]

        drift_reconcile = await async_client.post(
            f"/api/v1/enforcement/reservations/{drift_id}/reconcile",
            json={"actual_monthly_delta_usd": "80"},
        )
        assert drift_reconcile.status_code == 200

        matched_reconcile = await async_client.post(
            f"/api/v1/enforcement/reservations/{matched_id}/reconcile",
            json={"actual_monthly_delta_usd": "75"},
        )
        assert matched_reconcile.status_code == 200

        exceptions = await async_client.get(
            "/api/v1/enforcement/reservations/reconciliation-exceptions?limit=50"
        )
        assert exceptions.status_code == 200
        body = exceptions.json()
        ids = {item["decision_id"] for item in body}

        assert drift_id in ids
        assert matched_id not in ids
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_reconciliation_exceptions_endpoint_forbids_member(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    member_user = CurrentUser(
        id=uuid4(),
        email="member@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.MEMBER,
    )
    _override_user(async_client, member_user)

    try:
        response = await async_client.get(
            "/api/v1/enforcement/reservations/reconciliation-exceptions"
        )
        assert response.status_code == 403
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_enforcement_export_parity_and_archive_endpoints(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)

    try:
        first = await _create_pending_approval_via_api(
            async_client,
            idempotency_key="api-export-bundle-1",
            environment="nonprod",
            require_approval_for_prod=False,
            require_approval_for_nonprod=True,
        )
        second = await _create_pending_approval_via_api(
            async_client,
            idempotency_key="api-export-bundle-2",
            environment="prod",
            require_approval_for_prod=True,
            require_approval_for_nonprod=True,
        )
        assert first["approval_request_id"] is not None
        assert second["approval_request_id"] is not None

        parity = await async_client.get("/api/v1/enforcement/exports/parity")
        assert parity.status_code == 200
        parity_payload = parity.json()
        assert parity_payload["parity_ok"] is True
        assert parity_payload["decision_count_db"] == 2
        assert parity_payload["decision_count_exported"] == 2
        assert parity_payload["approval_count_db"] == 2
        assert parity_payload["approval_count_exported"] == 2
        assert len(parity_payload["decisions_sha256"]) == 64
        assert len(parity_payload["approvals_sha256"]) == 64
        assert len(parity_payload["policy_lineage_sha256"]) == 64
        assert parity_payload["policy_lineage_entries"] >= 1
        assert len(parity_payload["computed_context_lineage_sha256"]) == 64
        assert parity_payload["computed_context_lineage_entries"] >= 1
        assert len(parity_payload["manifest_content_sha256"]) == 64
        assert len(parity_payload["manifest_signature"]) == 64
        assert parity_payload["manifest_signature_algorithm"] == "hmac-sha256"
        assert len(parity_payload["manifest_signature_key_id"]) >= 1

        archive = await async_client.get("/api/v1/enforcement/exports/archive")
        assert archive.status_code == 200
        assert archive.headers["content-type"].startswith("application/zip")

        with zipfile.ZipFile(io.BytesIO(archive.content)) as bundle:
            names = set(bundle.namelist())
            assert "manifest.json" in names
            assert "manifest.canonical.json" in names
            assert "manifest.sha256" in names
            assert "manifest.sig" in names
            assert "decisions.csv" in names
            assert "approvals.csv" in names

            manifest_payload = json.loads(bundle.read("manifest.json").decode("utf-8"))
            assert manifest_payload["parity_ok"] is True
            assert manifest_payload["decision_count_db"] == 2
            assert manifest_payload["decision_count_exported"] == 2
            assert manifest_payload["approval_count_db"] == 2
            assert manifest_payload["approval_count_exported"] == 2
            assert len(manifest_payload["policy_lineage_sha256"]) == 64
            assert isinstance(manifest_payload["policy_lineage"], list)
            assert len(manifest_payload["policy_lineage"]) >= 1
            assert len(manifest_payload["computed_context_lineage_sha256"]) == 64
            assert isinstance(manifest_payload["computed_context_lineage"], list)
            assert len(manifest_payload["computed_context_lineage"]) >= 1
            canonical_manifest = bundle.read("manifest.canonical.json").decode("utf-8")
            canonical_manifest_sha256 = hashlib.sha256(
                canonical_manifest.encode("utf-8")
            ).hexdigest()
            assert canonical_manifest_sha256 == manifest_payload["manifest_content_sha256"]
            assert manifest_payload["manifest_content_sha256"] == parity_payload["manifest_content_sha256"]
            assert bundle.read("manifest.sha256").decode("utf-8").strip() == manifest_payload["manifest_content_sha256"]
            assert bundle.read("manifest.sig").decode("utf-8").strip() == manifest_payload["manifest_signature"]
            assert manifest_payload["manifest_signature"] == parity_payload["manifest_signature"]
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_enforcement_export_endpoints_forbid_member(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    member_user = CurrentUser(
        id=uuid4(),
        email="member@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.MEMBER,
    )
    _override_user(async_client, member_user)

    try:
        parity = await async_client.get("/api/v1/enforcement/exports/parity")
        archive = await async_client.get("/api/v1/enforcement/exports/archive")
        assert parity.status_code == 403
        assert archive.status_code == 403
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_decision_ledger_endpoint_admin(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)

    try:
        gate = await async_client.post(
            "/api/v1/enforcement/gate/terraform",
            json={
                "project_id": "default",
                "environment": "nonprod",
                "action": "terraform.apply",
                "resource_reference": "module.vpc.aws_vpc.main",
                "estimated_monthly_delta_usd": "20",
                "estimated_hourly_delta_usd": "0.03",
                "metadata": {"resource_type": "aws_vpc"},
                "idempotency_key": "api-ledger-1",
            },
        )
        assert gate.status_code == 200
        decision_id = gate.json()["decision_id"]

        ledger = await async_client.get("/api/v1/enforcement/ledger?limit=50")
        assert ledger.status_code == 200
        payload = ledger.json()
        assert len(payload) >= 1
        first = payload[0]
        assert first["decision_id"] == decision_id
        assert first["source"] == "terraform"
        assert first["burn_rate_daily_usd"] is not None
        assert first["forecast_eom_usd"] is not None
        assert first["risk_class"] in {"low", "medium", "high"}
        assert first["policy_document_schema_version"] == "valdrics.enforcement.policy.v1"
        assert len(first["policy_document_sha256"]) == 64
        assert first["approval_request_id"] is None
        assert first["approval_status"] is None
        assert len(first["request_payload_sha256"]) == 64
        assert len(first["response_payload_sha256"]) == 64
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_decision_ledger_endpoint_forbids_member(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    member_user = CurrentUser(
        id=uuid4(),
        email="member@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.MEMBER,
    )
    _override_user(async_client, member_user)

    try:
        response = await async_client.get("/api/v1/enforcement/ledger")
        assert response.status_code == 403
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_approval_queue_create_request_and_deny_endpoints(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)
    fake_queue_backlog = _FakeGauge()

    try:
        with patch(
            "app.modules.enforcement.api.v1.approvals.ENFORCEMENT_APPROVAL_QUEUE_BACKLOG",
            fake_queue_backlog,
        ):
            gate_payload = await _create_pending_approval_via_api(
                async_client,
                idempotency_key="api-approval-queue-create-deny-1",
                environment="nonprod",
                require_approval_for_prod=False,
                require_approval_for_nonprod=True,
            )
            approval_id = gate_payload["approval_request_id"]
            decision_id = gate_payload["decision_id"]
            assert approval_id is not None

            create = await async_client.post(
                "/api/v1/enforcement/approvals/requests",
                json={"decision_id": decision_id, "notes": "queue me"},
            )
            assert create.status_code == 200
            create_payload = create.json()
            assert create_payload["approval_id"] == approval_id
            assert create_payload["status"] == "pending"

            queue = await async_client.get("/api/v1/enforcement/approvals/queue?limit=50")
            assert queue.status_code == 200
            queue_ids = {item["approval_id"] for item in queue.json()}
            assert approval_id in queue_ids
            assert fake_queue_backlog.calls
            labels, value = fake_queue_backlog.calls[-1]
            assert labels["viewer_role"] == "admin"
            assert value >= 1.0

            deny = await async_client.post(
                f"/api/v1/enforcement/approvals/{approval_id}/deny",
                json={"notes": "denied by admin"},
            )
            assert deny.status_code == 200
            deny_payload = deny.json()
            assert deny_payload["status"] == "denied"
            assert deny_payload["approval_token"] is None
            assert deny_payload["token_expires_at"] is None
    finally:
        _clear_user_override(async_client)
