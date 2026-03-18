import pytest
import boto3
from moto import mock_aws
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import select
from httpx import AsyncClient
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.models.tenant import Tenant, User, UserRole
from app.models.aws_connection import AWSConnection
from app.models.optimization import FindingStatus, OptimizationFinding
from app.models.realized_savings import RealizedSavingsEvent
from app.models.remediation import RemediationRequest, RemediationStatus
from app.modules.reporting.domain.realized_savings import RealizedSavingsService
from app.shared.core.pricing import PricingTier
from tests.utils import create_test_token


@pytest.fixture(autouse=True)
async def cleanup_overrides():
    """Cleanup dependency overrides after each test."""
    from app.main import app

    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    import os

    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
async def setup_opt_data(db):
    """Setup a Pro tier tenant with an active AWS connection."""
    tenant = Tenant(id=uuid4(), name="Optimization Corp", plan=PricingTier.PRO.value)
    user = User(
        id=uuid4(), tenant_id=tenant.id, email="ops@optcorp.com", role=UserRole.ADMIN
    )

    conn = AWSConnection(
        id=uuid4(),
        tenant_id=tenant.id,
        aws_account_id="123456789012",
        role_arn="arn:aws:iam::123456789012:role/ValdricsTestRole",
        region="us-east-1",
        status="active",
    )

    db.add(tenant)
    db.add(user)
    db.add(conn)
    await db.commit()
    await db.refresh(tenant)
    await db.refresh(user)

    token = create_test_token(user.id, user.email)
    return {"tenant": tenant, "user": user, "token": token, "connection": conn}


class AsyncPaginatorWrapper:
    def __init__(self, sync_paginator):
        self._sync_paginator = sync_paginator

    def paginate(self, *args, **kwargs):
        self._iter = iter(self._sync_paginator.paginate(*args, **kwargs))
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class AsyncClientWrapper:
    """Wrapper to make boto3 sync clients behave like aioboto3 async clients."""

    def __init__(self, sync_client):
        self._sync_client = sync_client

    def __getattr__(self, name):
        attr = getattr(self._sync_client, name)
        if name == "get_paginator":

            def get_paginator_wrapper(*args, **kwargs):
                return AsyncPaginatorWrapper(attr(*args, **kwargs))

            return get_paginator_wrapper

        if callable(attr):

            async def wrapper(*args, **kwargs):
                # Execute directly in main thread for moto compatibility
                res = attr(*args, **kwargs)
                return res

            return wrapper
        return attr

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.mark.anyio
async def test_remediation_lifecycle_full(
    ac: AsyncClient, setup_opt_data, db, aws_credentials
):
    """Full remediation lifecycle integration test."""
    with mock_aws():
        # Setup mock AWS
        ec2 = boto3.client("ec2", region_name="us-east-1")
        run_instances = ec2.run_instances(
            ImageId="ami-12345678", MaxCount=1, MinCount=1, InstanceType="t2.micro"
        )
        instance_id = run_instances["Instances"][0]["InstanceId"]

        headers = {"Authorization": f"Bearer {setup_opt_data['token']}"}

        import aioboto3
        from app.shared.adapters.aws_multitenant import MultiTenantAWSAdapter

        def mock_client(self, service_name, **kwargs):
            return AsyncClientWrapper(
                boto3.client(service_name, region_name="us-east-1")
            )

        async def mock_get_credentials(self):
            return {
                "AccessKeyId": "testing",
                "SecretAccessKey": "testing",
                "SessionToken": "testing",
            }

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(aioboto3.Session, "client", mock_client)
            mp.setattr(MultiTenantAWSAdapter, "get_credentials", mock_get_credentials)
            fake_detector = SimpleNamespace(
                provider_name="aws",
                get_credentials=AsyncMock(
                    return_value={
                        "AccessKeyId": "testing",
                        "SecretAccessKey": "testing",
                        "SessionToken": "testing",
                    }
                ),
                scan_all=AsyncMock(
                    return_value={
                        "idle_instances": [
                            {
                                "resource_id": instance_id,
                                "resource_type": "ec2_instance",
                                "monthly_cost": 15.5,
                            }
                        ]
                    }
                ),
            )
            mp.setattr(
                "app.modules.optimization.domain.service.ZombieDetectorFactory",
                SimpleNamespace(get_detector=lambda *_args, **_kwargs: fake_detector),
            )
            mp.setattr(
                "app.modules.optimization.adapters.aws.region_discovery.RegionDiscovery.get_enabled_regions",
                AsyncMock(return_value=["us-east-1"]),
            )

            # 1. Run Scan
            response = await ac.get("/api/v1/zombies?region=us-east-1", headers=headers)
            assert response.status_code == 200
            scan_payload = response.json()
            finding_id = None
            for bucket in scan_payload.values():
                if not isinstance(bucket, list):
                    continue
                for item in bucket:
                    if not isinstance(item, dict):
                        continue
                    if item.get("resource_id") != instance_id:
                        continue
                    finding_id = item.get("finding_id")
                    if finding_id:
                        break
                if finding_id:
                    break
            assert finding_id

            # 2. Request Remediation
            req_payload = {
                "finding_id": finding_id,
                "action": "terminate_instance",
            }
            response = await ac.post(
                "/api/v1/zombies/request", json=req_payload, headers=headers
            )
            assert response.status_code == 200
            request_id = response.json()["request_id"]

            duplicate_response = await ac.post(
                "/api/v1/zombies/request", json=req_payload, headers=headers
            )
            assert duplicate_response.status_code == 409
            assert (
                duplicate_response.json()["error"]["code"]
                == "remediation_request_duplicate_open_finding"
            )

            # 3. Approve
            response = await ac.post(
                f"/api/v1/zombies/approve/{request_id}",
                json={"notes": "test"},
                headers=headers,
            )
            assert response.status_code == 200

            # 4. Execute
            response = await ac.post(
                f"/api/v1/zombies/execute/{request_id}?bypass_grace_period=true",
                headers=headers,
            )
            assert response.status_code == 200
            assert response.json()["status"] == "completed"

            # 5. Verify In Mock AWS
            desc = ec2.describe_instances(InstanceIds=[instance_id])
            assert desc["Reservations"][0]["Instances"][0]["State"]["Name"] in [
                "shutting-down",
                "terminated",
            ]

            # 6. Verify DB
            from uuid import UUID

            result = await db.execute(
                select(RemediationRequest).where(
                    RemediationRequest.id == UUID(request_id)
                )
            )
            rem = result.scalar_one()
            assert rem.status == RemediationStatus.COMPLETED
            assert rem.finding_id is not None
            rem.executed_at = datetime.now(timezone.utc) - timedelta(days=2)

            finding_result = await db.execute(
                select(OptimizationFinding).where(
                    OptimizationFinding.id == UUID(finding_id)
                )
            )
            finding = finding_result.scalar_one()
            assert finding.status == FindingStatus.RESOLVED

            service = RealizedSavingsService(db)
            with pytest.MonkeyPatch.context() as savings_mp:
                savings_mp.setattr(
                    service,
                    "_window_cost",
                    AsyncMock(side_effect=[(Decimal("12.00"), 1), (Decimal("3.00"), 1)]),
                )
                event = await service.compute_for_request(
                    tenant_id=setup_opt_data["tenant"].id,
                    request=rem,
                    baseline_days=1,
                    measurement_days=1,
                    gap_days=0,
                    monthly_multiplier_days=30,
                    require_final=False,
                )

            assert event is not None
            assert event.finding_id == rem.finding_id
            assert event.finding_category == "idle_instances"
            assert event.realized_monthly_savings_usd == Decimal("270.00")
            await db.commit()

            event_result = await db.execute(
                select(RealizedSavingsEvent).where(
                    RealizedSavingsEvent.remediation_request_id == rem.id
                )
            )
            persisted_event = event_result.scalar_one()
            assert persisted_event.finding_id == rem.finding_id
            assert persisted_event.finding_category == "idle_instances"
