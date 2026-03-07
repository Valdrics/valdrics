from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.shared.connections.discovery import DiscoveryWizardService
from tests.unit.shared.connections.discovery_service_test_helpers import (
    _BrokenMXRecord,
    _CNAMERecord,
    _FakeDB,
    _FakeResult,
    _MXRecord,
    _TXTRecord,
)


async def test_discover_stage_a_orchestrates_calls() -> None:
    service = DiscoveryWizardService(MagicMock())
    tenant_id = uuid4()
    fake_signals = {"mx_hosts": [], "txt_records": [], "cname_targets": {}}
    fake_drafts = [{"provider": "aws"}]
    fake_candidates = [{"id": "candidate-1"}]

    with (
        patch.object(
            service,
            "_collect_domain_signals",
            new=AsyncMock(return_value=(fake_signals, ["dns_warning"])),
        ),
        patch.object(
            service,
            "_build_stage_a_candidates",
            return_value=fake_drafts,
        ) as build_mock,
        patch.object(
            service,
            "_upsert_candidates",
            new=AsyncMock(return_value=fake_candidates),
        ) as upsert_mock,
    ):
        domain, candidates, warnings = await service.discover_stage_a(
            tenant_id, "Owner@Example.COM"
        )

    assert domain == "example.com"
    assert candidates == fake_candidates
    assert warnings == ["dns_warning"]
    build_mock.assert_called_once_with("example.com", fake_signals)
    upsert_mock.assert_awaited_once_with(tenant_id, "example.com", fake_drafts)


async def test_deep_scan_idp_microsoft_path_builds_default_cloud_inference() -> None:
    service = DiscoveryWizardService(MagicMock())
    tenant_id = uuid4()
    fake_connection = SimpleNamespace(api_key=" m365-token ")
    app_drafts = [
        {
            "category": "cloud_plus",
            "provider": "slack",
            "source": "idp_deep_scan",
            "confidence_score": 0.86,
            "requires_admin_auth": True,
            "connection_target": "saas",
            "connection_vendor_hint": "slack",
            "evidence": ["idp_app:Slack"],
            "details": {"matched_app_name": "Slack"},
        }
    ]

    with (
        patch.object(
            service,
            "_find_idp_license_connection",
            new=AsyncMock(return_value=fake_connection),
        ),
        patch.object(
            service,
            "_scan_microsoft_enterprise_apps",
            new=AsyncMock(return_value=(["Slack"], ["ms_warning"])),
        ),
        patch.object(service, "_build_app_name_candidates", return_value=app_drafts),
        patch.object(
            service,
            "_upsert_candidates",
            new=AsyncMock(return_value=[{"id": "stored"}]),
        ) as upsert_mock,
    ):
        domain, candidates, warnings = await service.deep_scan_idp(
            tenant_id, "Example.COM.", "microsoft_365"
        )

    assert domain == "example.com"
    assert candidates == [{"id": "stored"}]
    assert warnings == ["ms_warning"]

    drafts = upsert_mock.await_args.args[2]
    providers = {(item["category"], item["provider"]) for item in drafts}
    assert ("license", "microsoft_365") in providers
    assert ("cloud_provider", "azure") in providers
    assert ("cloud_plus", "slack") in providers


async def test_deep_scan_idp_google_path_uses_max_users() -> None:
    service = DiscoveryWizardService(MagicMock())
    tenant_id = uuid4()
    fake_connection = SimpleNamespace(api_key="google-token")

    with (
        patch.object(
            service,
            "_find_idp_license_connection",
            new=AsyncMock(return_value=fake_connection),
        ),
        patch.object(
            service,
            "_scan_google_workspace_apps",
            new=AsyncMock(return_value=(["GitHub"], ["gw_warning"])),
        ) as scan_mock,
        patch.object(service, "_build_app_name_candidates", return_value=[]),
        patch.object(service, "_upsert_candidates", new=AsyncMock(return_value=[])),
    ):
        domain, candidates, warnings = await service.deep_scan_idp(
            tenant_id, "corp.example.com", "google_workspace", max_users=7
        )

    assert domain == "corp.example.com"
    assert candidates == []
    assert warnings == ["gw_warning"]
    scan_mock.assert_awaited_once_with("google-token", max_users=7)


async def test_deep_scan_idp_validation_errors() -> None:
    service = DiscoveryWizardService(MagicMock())
    tenant_id = uuid4()

    with pytest.raises(ValueError, match="idp_provider must be"):
        await service.deep_scan_idp(tenant_id, "example.com", "okta")

    with patch.object(
        service, "_find_idp_license_connection", new=AsyncMock(return_value=None)
    ):
        with pytest.raises(ValueError, match="No active google_workspace"):
            await service.deep_scan_idp(tenant_id, "example.com", "google_workspace")

    with patch.object(
        service,
        "_find_idp_license_connection",
        new=AsyncMock(return_value=SimpleNamespace(api_key="   ")),
    ):
        with pytest.raises(ValueError, match="missing api_key token"):
            await service.deep_scan_idp(tenant_id, "example.com", "google_workspace")


async def test_list_candidates_validates_status_and_returns_scalars() -> None:
    rows = [SimpleNamespace(provider="aws"), SimpleNamespace(provider="gcp")]
    db = _FakeDB([_FakeResult(values=rows), _FakeResult(values=rows)])
    service = DiscoveryWizardService(db)

    assert await service.list_candidates(uuid4()) == rows
    assert await service.list_candidates(uuid4(), status="IGNORED") == rows

    with pytest.raises(ValueError, match="Invalid status"):
        await service.list_candidates(uuid4(), status="bad-status")


async def test_update_candidate_status_updates_existing_row() -> None:
    candidate = SimpleNamespace(status="pending", updated_at=None)
    db = _FakeDB([_FakeResult(one=candidate)])
    service = DiscoveryWizardService(db)

    updated = await service.update_candidate_status(uuid4(), uuid4(), "ACCEPTED")

    assert updated is candidate
    assert candidate.status == "accepted"
    assert isinstance(candidate.updated_at, datetime)
    assert candidate.updated_at.tzinfo is timezone.utc
    assert db.commits == 1
    assert db.refreshed == [candidate]


async def test_update_candidate_status_errors_for_invalid_status_and_missing_candidate() -> None:
    service = DiscoveryWizardService(_FakeDB([]))
    with pytest.raises(ValueError, match="Invalid status"):
        await service.update_candidate_status(uuid4(), uuid4(), "nonsense")

    missing_db = _FakeDB([_FakeResult(one=None)])
    missing_service = DiscoveryWizardService(missing_db)
    with pytest.raises(LookupError, match="not found"):
        await missing_service.update_candidate_status(uuid4(), uuid4(), "ignored")


async def test_upsert_candidates_creates_new_rows_and_updates_existing_rows() -> None:
    tenant_id = uuid4()
    existing = SimpleNamespace(
        confidence_score=0.30,
        source="domain_dns",
        requires_admin_auth=False,
        connection_target=None,
        connection_vendor_hint=None,
        evidence=[],
        details={"old": True},
        last_seen_at=None,
    )
    final_rows = [SimpleNamespace(id="final-1")]
    db = _FakeDB(
        [
            _FakeResult(one=existing),
            _FakeResult(one=None),
            _FakeResult(values=final_rows),
        ]
    )
    service = DiscoveryWizardService(db)

    drafts = [
        {
            "category": "cloud_provider",
            "provider": "azure",
            "source": "idp_deep_scan",
            "confidence_score": 0.91,
            "requires_admin_auth": True,
            "connection_target": "azure",
            "connection_vendor_hint": None,
            "evidence": ["idp_deep_scan:microsoft_365"],
            "details": {"new": True},
        },
        {
            "category": "cloud_provider",
            "provider": "aws",
            "source": "domain_dns",
            "confidence_score": 0.45,
            "requires_admin_auth": True,
            "connection_target": "aws",
            "connection_vendor_hint": None,
            "evidence": ["txt:amazonaws_or_amazonses"],
            "details": {"inference": "dns_txt_aws_signal"},
        },
    ]

    returned = await service._upsert_candidates(tenant_id, "example.com", drafts)

    assert returned == final_rows
    assert db.commits == 1
    assert len(db.added) == 1
    assert getattr(db.added[0], "provider") == "aws"
    assert existing.source == "idp_deep_scan"
    assert existing.confidence_score == pytest.approx(0.91)
    assert existing.connection_target == "azure"
    assert existing.details == {"new": True}
    assert existing.evidence == ["idp_deep_scan:microsoft_365"]
    assert isinstance(existing.last_seen_at, datetime)


async def test_upsert_candidates_preserves_existing_confidence_without_idp_upgrade() -> None:
    tenant_id = uuid4()
    existing = SimpleNamespace(
        confidence_score=0.95,
        source="domain_dns",
        requires_admin_auth=False,
        connection_target=None,
        connection_vendor_hint=None,
        evidence=["old-signal"],
        details={"old": True},
        last_seen_at=None,
    )
    final_rows = [existing]
    db = _FakeDB([_FakeResult(one=existing), _FakeResult(values=final_rows)])
    service = DiscoveryWizardService(db)

    drafts = [
        {
            "category": "cloud_provider",
            "provider": "azure",
            "source": "domain_dns",
            "confidence_score": 0.40,
            "requires_admin_auth": True,
            "connection_target": "azure",
            "connection_vendor_hint": None,
            "evidence": ["new-signal"],
            "details": {"new": True},
        }
    ]

    returned = await service._upsert_candidates(tenant_id, "example.com", drafts)

    assert returned == final_rows
    assert db.commits == 1
    assert existing.confidence_score == pytest.approx(0.95)
    assert existing.source == "domain_dns"
    assert existing.evidence == ["new-signal"]
    assert existing.details == {"new": True}


async def test_find_idp_license_connection_returns_first_result() -> None:
    connection = SimpleNamespace(vendor="microsoft_365")
    db = _FakeDB([_FakeResult(values=[connection]), _FakeResult(values=[connection])])
    service = DiscoveryWizardService(db)

    assert await service._find_idp_license_connection(uuid4(), "microsoft_365") is connection
    assert await service._find_idp_license_connection(uuid4(), "google_workspace") is connection


async def test_collect_domain_signals_runs_all_dns_probes() -> None:
    service = DiscoveryWizardService(MagicMock())

    async def fake_resolve(
        _resolver: object, name: str, record_type: str, warnings: list[str]
    ) -> list[str]:
        assert warnings == []
        if record_type == "MX":
            return ["aspmx.l.google.com"]
        if record_type == "TXT":
            return ["v=spf1 include:_spf.google.com ~all"]
        if name.startswith("slack."):
            return ["acme.slack.com"]
        if name.startswith("mail."):
            return ["mx1.mailhost.com"]
        return []

    with (
        patch(
            "app.shared.connections.discovery.dns.asyncresolver.Resolver",
            return_value=MagicMock(),
        ),
        patch.object(
            service, "_resolve_dns_records", new=AsyncMock(side_effect=fake_resolve)
        ) as resolve_mock,
    ):
        signals, warnings = await service._collect_domain_signals("example.com")

    assert warnings == []
    assert signals["mx_hosts"] == ["aspmx.l.google.com"]
    assert signals["txt_records"] == ["v=spf1 include:_spf.google.com ~all"]
    assert signals["cname_targets"]["slack.example.com"] == "acme.slack.com"
    assert signals["cname_targets"]["mail.example.com"] == "mx1.mailhost.com"
    assert resolve_mock.await_count == 13


async def test_resolve_dns_records_parses_supported_record_types_and_failures() -> None:
    service = DiscoveryWizardService(MagicMock())
    warnings: list[str] = []

    resolver = MagicMock()
    resolver.resolve = AsyncMock(return_value=[_MXRecord("ASPMX.L.GOOGLE.COM."), _BrokenMXRecord()])
    mx_values = await service._resolve_dns_records(resolver, "example.com", "MX", warnings)
    assert mx_values == ["aspmx.l.google.com"]

    resolver.resolve = AsyncMock(return_value=[_CNAMERecord("Acme.Slack.COM.")])
    cname_values = await service._resolve_dns_records(
        resolver, "slack.example.com", "CNAME", warnings
    )
    assert cname_values == ["acme.slack.com"]

    resolver.resolve = AsyncMock(return_value=[_TXTRecord('"ZoomSiteVerify=abc123"')])
    txt_values = await service._resolve_dns_records(resolver, "example.com", "TXT", warnings)
    assert txt_values == ["zoomsiteverify=abc123"]

    resolver.resolve = AsyncMock(return_value=["RAW-VALUE"])
    raw_values = await service._resolve_dns_records(resolver, "example.com", "SRV", warnings)
    assert raw_values == ["raw-value"]

    resolver.resolve = AsyncMock(return_value=None)
    assert await service._resolve_dns_records(resolver, "example.com", "TXT", warnings) == []

    resolver.resolve = AsyncMock(side_effect=RuntimeError("dns down"))
    assert await service._resolve_dns_records(resolver, "example.com", "TXT", warnings) == []
    assert any("TXT lookup failed for example.com" in message for message in warnings)

