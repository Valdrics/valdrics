from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.shared.connections.discovery import DiscoveryWizardService


def test_build_stage_a_candidates_detects_multiple_signal_types() -> None:
    service = DiscoveryWizardService(MagicMock())
    signals = {
        "mx_hosts": ["aspmx.l.google.com", "example.mail.protection.outlook.com"],
        "txt_records": [
            "v=spf1 include:_spf.google.com include:spf.protection.outlook.com ~all",
            "slack-domain-verification=abc123",
            "stripe-verification=xyz789",
            "zoomsiteverify=zoom123",
            "newrelic-domain-verification=nr123",
            "amazonaws.com",
        ],
        "cname_targets": {
            "autodiscover.example.com": "autodiscover.outlook.com",
            "slack.example.com": "acme.slack.com",
            "stripe.example.com": "billing.stripe.com",
            "salesforce.example.com": "org.my.salesforce.com",
            "zoom.example.com": "acme.zoom.us",
            "datadog.example.com": "acme.datadoghq.com",
            "newrelic.example.com": "acme.newrelic.com",
            "github.example.com": "acme.github.io",
        },
    }

    drafts = service._build_stage_a_candidates("example.com", signals)
    providers = {draft["provider"] for draft in drafts}
    expected = {
        "google_workspace",
        "gcp",
        "microsoft_365",
        "azure",
        "slack",
        "stripe",
        "salesforce",
        "zoom",
        "datadog",
        "newrelic",
        "github",
        "aws",
    }
    assert expected.issubset(providers)

    google_draft = next(item for item in drafts if item["provider"] == "google_workspace")
    microsoft_draft = next(item for item in drafts if item["provider"] == "microsoft_365")
    assert google_draft["confidence_score"] == pytest.approx(0.93)
    assert microsoft_draft["confidence_score"] == pytest.approx(0.93)


def test_build_stage_a_candidates_exercises_partial_and_fallback_paths() -> None:
    service = DiscoveryWizardService(MagicMock())

    google_spf_only = service._build_stage_a_candidates(
        "example.com",
        {
            "mx_hosts": [],
            "txt_records": ["v=spf1 include:_spf.google.com ~all"],
            "cname_targets": {},
        },
    )
    providers = {draft["provider"] for draft in google_spf_only}
    assert providers == {"google_workspace", "gcp"}
    assert next(item for item in google_spf_only if item["provider"] == "google_workspace")[
        "confidence_score"
    ] == pytest.approx(0.82)

    google_mx_only = service._build_stage_a_candidates(
        "example.com",
        {
            "mx_hosts": ["aspmx.l.google.com"],
            "txt_records": [],
            "cname_targets": {},
        },
    )
    providers = {draft["provider"] for draft in google_mx_only}
    assert providers == {"google_workspace", "gcp"}

    microsoft_autodiscover_only = service._build_stage_a_candidates(
        "example.com",
        {
            "mx_hosts": [],
            "txt_records": [],
            "cname_targets": {"autodiscover.example.com": "autodiscover.outlook.com"},
        },
    )
    providers = {draft["provider"] for draft in microsoft_autodiscover_only}
    assert providers == {"microsoft_365", "azure"}
    ms365 = next(item for item in microsoft_autodiscover_only if item["provider"] == "microsoft_365")
    assert ms365["evidence"] == ["cname:autodiscover"]

    microsoft_mx_only = service._build_stage_a_candidates(
        "example.com",
        {
            "mx_hosts": ["example.mail.protection.outlook.com"],
            "txt_records": [],
            "cname_targets": {},
        },
    )
    providers = {draft["provider"] for draft in microsoft_mx_only}
    assert providers == {"microsoft_365", "azure"}
    ms365 = next(item for item in microsoft_mx_only if item["provider"] == "microsoft_365")
    assert ms365["evidence"] == ["mx:microsoft"]


def test_build_app_name_candidates_maps_known_keywords_and_ignores_blank_values() -> None:
    service = DiscoveryWizardService(MagicMock())
    app_names = [
        " Amazon Web Services ",
        "Microsoft Azure",
        "Google Cloud BigQuery",
        "Stripe Billing",
        "Slack",
        "GitHub Enterprise",
        "Zoom",
        "SFDC CPQ",
        "Datadog",
        "New Relic One",
        "   ",
    ]

    drafts = service._build_app_name_candidates(app_names)
    providers = {draft["provider"] for draft in drafts}
    assert {
        "aws",
        "azure",
        "gcp",
        "stripe",
        "slack",
        "github",
        "zoom",
        "salesforce",
        "datadog",
        "newrelic",
    }.issubset(providers)
    assert all(draft["source"] == "idp_deep_scan" for draft in drafts)


def test_merge_drafts_prefers_higher_confidence_and_merges_evidence() -> None:
    service = DiscoveryWizardService(MagicMock())
    drafts = [
        {
            "category": "cloud_provider",
            "provider": "azure",
            "source": "domain_dns",
            "confidence_score": 0.62,
            "requires_admin_auth": False,
            "connection_target": "azure",
            "connection_vendor_hint": None,
            "evidence": ["signal-a", "signal-a"],
            "details": {"from": "dns"},
        },
        {
            "category": "cloud_provider",
            "provider": "azure",
            "source": "idp_deep_scan",
            "confidence_score": 0.91,
            "requires_admin_auth": True,
            "connection_target": "azure",
            "connection_vendor_hint": "microsoft_365",
            "evidence": ["signal-b"],
            "details": {"from": "idp"},
        },
        {
            "category": "cloud_provider",
            "provider": "azure",
            "source": "domain_dns",
            "confidence_score": 0.30,
            "requires_admin_auth": True,
            "connection_target": "azure",
            "connection_vendor_hint": None,
            "evidence": ["signal-b", "signal-c"],
            "details": {"from": "low"},
        },
    ]

    merged = service._merge_drafts(drafts)
    assert len(merged) == 1
    item = merged[0]
    assert item["confidence_score"] == pytest.approx(0.91)
    assert item["source"] == "idp_deep_scan"
    assert item["requires_admin_auth"] is True
    assert item["connection_vendor_hint"] == "microsoft_365"
    assert item["details"] == {"from": "idp"}
    assert item["evidence"] == ["signal-a", "signal-b", "signal-c"]


def test_normalize_domain_helpers() -> None:
    service = DiscoveryWizardService(MagicMock())

    assert service._normalize_email_domain("Admin@Example.COM") == "example.com"
    assert service._normalize_domain("Example.com.") == "example.com"

    with pytest.raises(ValueError, match="email must contain a valid domain"):
        service._normalize_email_domain("not-an-email")

    with pytest.raises(ValueError, match="fully qualified"):
        service._normalize_domain("localhost")

