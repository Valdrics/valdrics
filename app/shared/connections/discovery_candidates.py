from __future__ import annotations

from typing import Any


def build_stage_a_candidates(domain: str, signals: dict[str, Any]) -> list[dict[str, Any]]:
    mx_hosts = [str(v).lower() for v in signals.get("mx_hosts", [])]
    txt_records = [str(v).lower() for v in signals.get("txt_records", [])]
    cname_targets = {
        str(k).lower(): str(v).lower()
        for k, v in (signals.get("cname_targets") or {}).items()
    }
    cname_values = list(cname_targets.values())

    drafts: list[dict[str, Any]] = []

    has_google_mx = any(
        ("google.com" in host) or ("googlemail.com" in host) for host in mx_hosts
    )
    has_google_spf = any("include:_spf.google.com" in txt for txt in txt_records)
    if has_google_mx or has_google_spf:
        evidence = []
        if has_google_mx:
            evidence.append("mx:google")
        if has_google_spf:
            evidence.append("spf:google")
        confidence = 0.93 if (has_google_mx and has_google_spf) else 0.82
        drafts.extend(
            [
                {
                    "category": "license",
                    "provider": "google_workspace",
                    "source": "domain_dns",
                    "confidence_score": confidence,
                    "requires_admin_auth": True,
                    "connection_target": "license",
                    "connection_vendor_hint": "google_workspace",
                    "evidence": evidence,
                    "details": {"domain": domain},
                },
                {
                    "category": "cloud_provider",
                    "provider": "gcp",
                    "source": "domain_dns",
                    "confidence_score": 0.62,
                    "requires_admin_auth": True,
                    "connection_target": "gcp",
                    "connection_vendor_hint": None,
                    "evidence": evidence,
                    "details": {"inference": "google_workspace_domain_signals"},
                },
            ]
        )

    has_ms_mx = any("protection.outlook.com" in host for host in mx_hosts)
    has_ms_spf = any(
        "include:spf.protection.outlook.com" in txt for txt in txt_records
    )
    has_ms_autodiscover = any("outlook.com" in v for v in cname_values)
    if has_ms_mx or has_ms_spf or has_ms_autodiscover:
        evidence = []
        if has_ms_mx:
            evidence.append("mx:microsoft")
        if has_ms_spf:
            evidence.append("spf:microsoft")
        if has_ms_autodiscover:
            evidence.append("cname:autodiscover")
        confidence = 0.93 if (has_ms_mx and has_ms_spf) else 0.82
        drafts.extend(
            [
                {
                    "category": "license",
                    "provider": "microsoft_365",
                    "source": "domain_dns",
                    "confidence_score": confidence,
                    "requires_admin_auth": True,
                    "connection_target": "license",
                    "connection_vendor_hint": "microsoft_365",
                    "evidence": evidence,
                    "details": {"domain": domain},
                },
                {
                    "category": "cloud_provider",
                    "provider": "azure",
                    "source": "domain_dns",
                    "confidence_score": 0.62,
                    "requires_admin_auth": True,
                    "connection_target": "azure",
                    "connection_vendor_hint": None,
                    "evidence": evidence,
                    "details": {"inference": "microsoft_365_domain_signals"},
                },
            ]
        )

    has_slack_signal = any("slack" in val for val in cname_values) or any(
        "slack-domain-verification" in txt for txt in txt_records
    )
    if has_slack_signal:
        drafts.append(
            {
                "category": "cloud_plus",
                "provider": "slack",
                "source": "domain_dns",
                "confidence_score": 0.72,
                "requires_admin_auth": True,
                "connection_target": "saas",
                "connection_vendor_hint": "slack",
                "evidence": ["cname_or_txt:slack"],
                "details": {"domain": domain},
            }
        )

    has_stripe_signal = any("stripe" in val for val in cname_values) or any(
        "stripe-verification" in txt for txt in txt_records
    )
    if has_stripe_signal:
        drafts.append(
            {
                "category": "cloud_plus",
                "provider": "stripe",
                "source": "domain_dns",
                "confidence_score": 0.68,
                "requires_admin_auth": True,
                "connection_target": "saas",
                "connection_vendor_hint": "stripe",
                "evidence": ["cname_or_txt:stripe"],
                "details": {"domain": domain},
            }
        )

    has_salesforce_signal = any(
        ("salesforce.com" in val) or ("force.com" in val) for val in cname_values
    )
    if has_salesforce_signal:
        drafts.append(
            {
                "category": "cloud_plus",
                "provider": "salesforce",
                "source": "domain_dns",
                "confidence_score": 0.68,
                "requires_admin_auth": True,
                "connection_target": "saas",
                "connection_vendor_hint": "salesforce",
                "evidence": ["cname:salesforce_or_force"],
                "details": {"domain": domain},
            }
        )

    has_zoom_signal = any(
        ("zoom.us" in val) or ("zoom.com" in val) for val in cname_values
    ) or any(
        ("zoom-verification" in txt) or ("zoomsiteverify" in txt)
        for txt in txt_records
    )
    if has_zoom_signal:
        drafts.append(
            {
                "category": "cloud_plus",
                "provider": "zoom",
                "source": "domain_dns",
                "confidence_score": 0.64,
                "requires_admin_auth": True,
                "connection_target": "saas",
                "connection_vendor_hint": "zoom",
                "evidence": ["cname_or_txt:zoom"],
                "details": {"domain": domain},
            }
        )

    has_datadog_signal = any(
        ("datadoghq.com" in val) or ("ddog-gov.com" in val) for val in cname_values
    ) or any("datadog" in txt for txt in txt_records)
    if has_datadog_signal:
        drafts.append(
            {
                "category": "platform",
                "provider": "datadog",
                "source": "domain_dns",
                "confidence_score": 0.66,
                "requires_admin_auth": True,
                "connection_target": "platform",
                "connection_vendor_hint": "datadog",
                "evidence": ["cname_or_txt:datadog"],
                "details": {"domain": domain},
            }
        )

    has_newrelic_signal = any("newrelic" in val for val in cname_values) or any(
        "newrelic" in txt for txt in txt_records
    )
    if has_newrelic_signal:
        drafts.append(
            {
                "category": "platform",
                "provider": "newrelic",
                "source": "domain_dns",
                "confidence_score": 0.66,
                "requires_admin_auth": True,
                "connection_target": "platform",
                "connection_vendor_hint": "newrelic",
                "evidence": ["cname_or_txt:newrelic"],
                "details": {"domain": domain},
            }
        )

    has_github_signal = any(
        ("github.io" in val)
        or ("githubusercontent.com" in val)
        or ("github.com" in val)
        for val in cname_values
    )
    if has_github_signal:
        drafts.append(
            {
                "category": "cloud_plus",
                "provider": "github",
                "source": "domain_dns",
                "confidence_score": 0.60,
                "requires_admin_auth": True,
                "connection_target": "saas",
                "connection_vendor_hint": "github",
                "evidence": ["cname:github_pages"],
                "details": {"domain": domain},
            }
        )

    has_aws_signal = any(
        ("amazonses.com" in txt) or ("amazonaws.com" in txt) for txt in txt_records
    )
    if has_aws_signal:
        drafts.append(
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
            }
        )

    return drafts


def build_app_name_candidates(app_names: list[str]) -> list[dict[str, Any]]:
    drafts: list[dict[str, Any]] = []
    mappings = [
        (
            "cloud_provider",
            "aws",
            "aws",
            None,
            (
                "amazon web services",
                "aws",
                "iam identity center",
                "aws single sign-on",
            ),
            0.9,
        ),
        (
            "cloud_provider",
            "azure",
            "azure",
            None,
            ("azure", "microsoft azure"),
            0.84,
        ),
        (
            "cloud_provider",
            "gcp",
            "gcp",
            None,
            ("google cloud", "gcp", "bigquery", "cloud run"),
            0.86,
        ),
        (
            "cloud_plus",
            "stripe",
            "saas",
            "stripe",
            ("stripe",),
            0.86,
        ),
        (
            "cloud_plus",
            "slack",
            "saas",
            "slack",
            ("slack",),
            0.86,
        ),
        (
            "cloud_plus",
            "github",
            "saas",
            "github",
            ("github",),
            0.86,
        ),
        (
            "cloud_plus",
            "zoom",
            "saas",
            "zoom",
            ("zoom",),
            0.84,
        ),
        (
            "cloud_plus",
            "salesforce",
            "saas",
            "salesforce",
            ("salesforce", "sfdc"),
            0.88,
        ),
        (
            "platform",
            "datadog",
            "platform",
            "datadog",
            ("datadog",),
            0.84,
        ),
        (
            "platform",
            "newrelic",
            "platform",
            "newrelic",
            ("new relic", "newrelic"),
            0.84,
        ),
    ]

    for raw_name in app_names:
        name = raw_name.strip()
        if not name:
            continue
        lowered = name.lower()
        for category, provider, target, vendor_hint, keywords, confidence in mappings:
            if any(keyword in lowered for keyword in keywords):
                drafts.append(
                    {
                        "category": category,
                        "provider": provider,
                        "source": "idp_deep_scan",
                        "confidence_score": confidence,
                        "requires_admin_auth": True,
                        "connection_target": target,
                        "connection_vendor_hint": vendor_hint,
                        "evidence": [f"idp_app:{name}"],
                        "details": {"matched_app_name": name},
                    }
                )
    return drafts


def merge_drafts(drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for draft in drafts:
        key = (str(draft["category"]), str(draft["provider"]))
        existing = merged.get(key)
        if existing is None:
            merged[key] = {
                **draft,
                "evidence": list(dict.fromkeys(draft.get("evidence", []))),
            }
            continue

        if float(draft.get("confidence_score", 0.0)) > float(
            existing.get("confidence_score", 0.0)
        ):
            existing["confidence_score"] = float(draft["confidence_score"])
            existing["source"] = str(draft.get("source", existing.get("source")))
            existing["details"] = dict(
                draft.get("details") or existing.get("details") or {}
            )
            existing["connection_target"] = draft.get(
                "connection_target", existing.get("connection_target")
            )
            existing["connection_vendor_hint"] = draft.get(
                "connection_vendor_hint", existing.get("connection_vendor_hint")
            )
            existing["requires_admin_auth"] = bool(
                draft.get("requires_admin_auth", existing.get("requires_admin_auth"))
            )

        existing_evidence = list(existing.get("evidence", []))
        for signal in draft.get("evidence", []):
            if signal not in existing_evidence:
                existing_evidence.append(signal)
        existing["evidence"] = existing_evidence

    return list(merged.values())
