from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import dns.asyncresolver
import dns.exception
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.discovery_candidate import DiscoveryCandidate
from app.models.license_connection import LicenseConnection
from app.shared.connections.discovery_candidates import (
    build_app_name_candidates,
    build_stage_a_candidates,
    merge_drafts,
)
from app.shared.connections.discovery_idp import (
    request_json,
    scan_google_workspace_apps,
    scan_microsoft_enterprise_apps,
)
from app.shared.core.http import get_http_client

logger = structlog.get_logger()
DNS_RESOLUTION_RECOVERABLE_EXCEPTIONS = (
    dns.exception.DNSException,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)
DNS_RECORD_COERCION_RECOVERABLE_EXCEPTIONS = (
    AttributeError,
    RuntimeError,
    TypeError,
    ValueError,
)

_MICROSOFT_LICENSE_VENDORS = {"microsoft_365", "microsoft365", "m365", "microsoft"}
_GOOGLE_LICENSE_VENDORS = {"google_workspace", "googleworkspace", "gsuite", "google"}

_DISCOVERY_STATUS_VALUES = {"pending", "accepted", "ignored", "connected"}


class DiscoveryWizardService:
    """
    Discovery wizard orchestration.

    Stage A:
    - Domain signals (MX, TXT, selected CNAME probes) to produce probable candidates.

    Stage B:
    - Best-effort IdP deep scan using an active License connector token
      (Microsoft Graph service principals; Google Workspace token sampling).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def discover_stage_a(
        self, tenant_id: UUID, email: str
    ) -> tuple[str, list[DiscoveryCandidate], list[str]]:
        domain = self._normalize_email_domain(email)
        signals, warnings = await self._collect_domain_signals(domain)
        drafts = self._build_stage_a_candidates(domain, signals)
        candidates = await self._upsert_candidates(tenant_id, domain, drafts)
        return domain, candidates, warnings

    async def deep_scan_idp(
        self,
        tenant_id: UUID,
        domain: str,
        idp_provider: str,
        *,
        max_users: int = 20,
    ) -> tuple[str, list[DiscoveryCandidate], list[str]]:
        normalized_domain = self._normalize_domain(domain)
        provider = idp_provider.strip().lower()
        if provider not in {"microsoft_365", "google_workspace"}:
            raise ValueError("idp_provider must be microsoft_365 or google_workspace")

        connection = await self._find_idp_license_connection(tenant_id, provider)
        if connection is None:
            raise ValueError(
                f"No active {provider} license connector found. "
                "Connect and verify License connector first, then run deep scan."
            )

        token = (connection.api_key or "").strip()
        if not token:
            raise ValueError(
                f"{provider} license connector is missing api_key token for deep scan."
            )

        warnings: list[str] = []
        if provider == "microsoft_365":
            app_names, provider_warnings = await self._scan_microsoft_enterprise_apps(
                token
            )
            warnings.extend(provider_warnings)
        else:
            app_names, provider_warnings = await self._scan_google_workspace_apps(
                token, max_users=max_users
            )
            warnings.extend(provider_warnings)

        drafts: list[dict[str, Any]] = [
            {
                "category": "license",
                "provider": provider,
                "source": "idp_deep_scan",
                "confidence_score": 0.99,
                "requires_admin_auth": True,
                "connection_target": "license",
                "connection_vendor_hint": provider,
                "evidence": [f"idp_deep_scan:{provider}"],
                "details": {
                    "idp_provider": provider,
                    "detected_apps": len(app_names),
                },
            }
        ]

        # Strong default cloud inference from primary identity provider.
        if provider == "microsoft_365":
            drafts.append(
                {
                    "category": "cloud_provider",
                    "provider": "azure",
                    "source": "idp_deep_scan",
                    "confidence_score": 0.82,
                    "requires_admin_auth": True,
                    "connection_target": "azure",
                    "connection_vendor_hint": None,
                    "evidence": ["idp_deep_scan:microsoft_365"],
                    "details": {"inference": "entra_primary_idp"},
                }
            )
        else:
            drafts.append(
                {
                    "category": "cloud_provider",
                    "provider": "gcp",
                    "source": "idp_deep_scan",
                    "confidence_score": 0.82,
                    "requires_admin_auth": True,
                    "connection_target": "gcp",
                    "connection_vendor_hint": None,
                    "evidence": ["idp_deep_scan:google_workspace"],
                    "details": {"inference": "google_workspace_primary_idp"},
                }
            )

        drafts.extend(self._build_app_name_candidates(app_names))
        candidates = await self._upsert_candidates(tenant_id, normalized_domain, drafts)
        return normalized_domain, candidates, warnings

    async def list_candidates(
        self, tenant_id: UUID, *, status: str | None = None
    ) -> list[DiscoveryCandidate]:
        stmt = select(DiscoveryCandidate).where(DiscoveryCandidate.tenant_id == tenant_id)
        if status:
            normalized_status = status.strip().lower()
            if normalized_status not in _DISCOVERY_STATUS_VALUES:
                raise ValueError(
                    f"Invalid status '{status}'. Expected one of: "
                    f"{', '.join(sorted(_DISCOVERY_STATUS_VALUES))}."
                )
            stmt = stmt.where(DiscoveryCandidate.status == normalized_status)
        stmt = stmt.order_by(
            DiscoveryCandidate.confidence_score.desc(),
            DiscoveryCandidate.provider.asc(),
            DiscoveryCandidate.created_at.desc(),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_candidate_status(
        self, tenant_id: UUID, candidate_id: UUID, status: str
    ) -> DiscoveryCandidate:
        normalized_status = status.strip().lower()
        if normalized_status not in _DISCOVERY_STATUS_VALUES:
            raise ValueError(
                f"Invalid status '{status}'. Expected one of: "
                f"{', '.join(sorted(_DISCOVERY_STATUS_VALUES))}."
            )

        result = await self.db.execute(
            select(DiscoveryCandidate).where(
                DiscoveryCandidate.id == candidate_id,
                DiscoveryCandidate.tenant_id == tenant_id,
            )
        )
        candidate = result.scalar_one_or_none()
        if candidate is None:
            raise LookupError("Discovery candidate not found")

        candidate.status = normalized_status
        candidate.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(candidate)
        return candidate

    async def _upsert_candidates(
        self,
        tenant_id: UUID,
        domain: str,
        drafts: list[dict[str, Any]],
    ) -> list[DiscoveryCandidate]:
        now = datetime.now(timezone.utc)
        merged = self._merge_drafts(drafts)
        for draft in merged:
            existing_result = await self.db.execute(
                select(DiscoveryCandidate).where(
                    DiscoveryCandidate.tenant_id == tenant_id,
                    DiscoveryCandidate.domain == domain,
                    DiscoveryCandidate.category == draft["category"],
                    DiscoveryCandidate.provider == draft["provider"],
                )
            )
            existing = existing_result.scalar_one_or_none()
            if existing is None:
                self.db.add(
                    DiscoveryCandidate(
                        tenant_id=tenant_id,
                        domain=domain,
                        category=draft["category"],
                        provider=draft["provider"],
                        source=draft["source"],
                        status="pending",
                        confidence_score=float(draft["confidence_score"]),
                        requires_admin_auth=bool(draft["requires_admin_auth"]),
                        connection_target=draft.get("connection_target"),
                        connection_vendor_hint=draft.get("connection_vendor_hint"),
                        evidence=list(draft["evidence"]),
                        details=dict(draft["details"]),
                        last_seen_at=now,
                    )
                )
                continue

            existing.last_seen_at = now
            existing.requires_admin_auth = bool(draft["requires_admin_auth"])
            existing.connection_target = draft.get("connection_target")
            existing.connection_vendor_hint = draft.get("connection_vendor_hint")
            existing.evidence = list(draft["evidence"])
            existing.details = dict(draft["details"])

            incoming_confidence = float(draft["confidence_score"])
            # Do not silently downgrade confidence or source quality.
            if (
                incoming_confidence > float(existing.confidence_score)
                or draft["source"] == "idp_deep_scan"
            ):
                existing.confidence_score = incoming_confidence
                existing.source = draft["source"]

        await self.db.commit()
        result = await self.db.execute(
            select(DiscoveryCandidate)
            .where(
                DiscoveryCandidate.tenant_id == tenant_id,
                DiscoveryCandidate.domain == domain,
            )
            .order_by(
                DiscoveryCandidate.confidence_score.desc(),
                DiscoveryCandidate.provider.asc(),
            )
        )
        return list(result.scalars().all())

    async def _find_idp_license_connection(
        self, tenant_id: UUID, idp_provider: str
    ) -> LicenseConnection | None:
        aliases = (
            _MICROSOFT_LICENSE_VENDORS
            if idp_provider == "microsoft_365"
            else _GOOGLE_LICENSE_VENDORS
        )
        result = await self.db.execute(
            select(LicenseConnection)
            .where(
                LicenseConnection.tenant_id == tenant_id,
                LicenseConnection.vendor.in_(aliases),
                LicenseConnection.auth_method.in_(("api_key", "oauth")),
                LicenseConnection.api_key.is_not(None),
                LicenseConnection.is_active.is_(True),
            )
            .order_by(LicenseConnection.last_synced_at.desc())
        )
        return result.scalars().first()

    async def _collect_domain_signals(
        self, domain: str
    ) -> tuple[dict[str, Any], list[str]]:
        warnings: list[str] = []
        resolver = dns.asyncresolver.Resolver(configure=True)
        resolver.timeout = 2.0
        resolver.lifetime = 4.0

        mx_hosts = await self._resolve_dns_records(resolver, domain, "MX", warnings)
        txt_records = await self._resolve_dns_records(resolver, domain, "TXT", warnings)

        cname_targets: dict[str, str] = {}
        for prefix in (
            "autodiscover",
            "enterpriseenrollment",
            "enterpriseregistration",
            "slack",
            "stripe",
            "zoom",
            "datadog",
            "newrelic",
            "chat",
            "www",
            "mail",
        ):
            host = f"{prefix}.{domain}"
            values = await self._resolve_dns_records(resolver, host, "CNAME", warnings)
            if values:
                cname_targets[host] = values[0]

        return {
            "mx_hosts": mx_hosts,
            "txt_records": txt_records,
            "cname_targets": cname_targets,
        }, warnings

    async def _resolve_dns_records(
        self,
        resolver: dns.asyncresolver.Resolver,
        name: str,
        record_type: str,
        warnings: list[str],
    ) -> list[str]:
        try:
            answer = await resolver.resolve(name, record_type, raise_on_no_answer=False)
            if answer is None:
                return []
        except DNS_RESOLUTION_RECOVERABLE_EXCEPTIONS as exc:
            warnings.append(f"{record_type} lookup failed for {name}: {exc}")
            return []

        values: list[str] = []
        for record in answer:
            try:
                if record_type == "MX":
                    host = str(record.exchange).strip().rstrip(".").lower()
                    values.append(host)
                elif record_type == "CNAME":
                    target = str(record.target).strip().rstrip(".").lower()
                    values.append(target)
                elif record_type == "TXT":
                    text = record.to_text().strip().strip('"').lower()
                    values.append(text)
                else:
                    values.append(str(record).strip().lower())
            except DNS_RECORD_COERCION_RECOVERABLE_EXCEPTIONS:
                continue
        return values

    def _build_stage_a_candidates(
        self, domain: str, signals: dict[str, Any]
    ) -> list[dict[str, Any]]:
        return build_stage_a_candidates(domain, signals)

    def _build_app_name_candidates(self, app_names: list[str]) -> list[dict[str, Any]]:
        return build_app_name_candidates(app_names)

    async def _scan_microsoft_enterprise_apps(
        self, token: str
    ) -> tuple[list[str], list[str]]:
        return await scan_microsoft_enterprise_apps(token, request_json_fn=self._request_json)

    async def _scan_google_workspace_apps(
        self, token: str, *, max_users: int
    ) -> tuple[list[str], list[str]]:
        return await scan_google_workspace_apps(
            token,
            max_users=max_users,
            request_json_fn=self._request_json,
        )

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        allow_404: bool = False,
    ) -> dict[str, Any]:
        return await request_json(
            method,
            url,
            headers=headers,
            allow_404=allow_404,
            get_http_client_fn=get_http_client,
            attempt_values=range(1, 4),
        )

    def _merge_drafts(self, drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return merge_drafts(drafts)

    def _normalize_email_domain(self, email: str) -> str:
        value = str(email or "").strip().lower()
        if "@" not in value:
            raise ValueError("email must contain a valid domain")
        return self._normalize_domain(value.split("@", 1)[1])

    def _normalize_domain(self, domain: str) -> str:
        normalized = str(domain or "").strip().lower().strip(".")
        if "." not in normalized:
            raise ValueError("domain must be fully qualified, e.g. example.com")
        return normalized
