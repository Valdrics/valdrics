from __future__ import annotations

from fastapi import HTTPException

SUPPORTED_PROVIDER_FILTERS = {
    "aws",
    "azure",
    "gcp",
    "saas",
    "license",
    "platform",
    "hybrid",
}
SUPPORTED_SPEND_LEDGER_PROVIDER_FILTERS = {*SUPPORTED_PROVIDER_FILTERS, "ai"}
SUPPORTED_FOCUS_EXPORT_PROVIDER_FILTERS = {*SUPPORTED_PROVIDER_FILTERS, "ai"}
SUPPORTED_ANOMALY_SEVERITIES = {"low", "medium", "high", "critical"}


def normalize_provider_filter(provider: str | None) -> str | None:
    return _normalize_with_supported(provider, SUPPORTED_PROVIDER_FILTERS)


def normalize_spend_ledger_provider_filter(provider: str | None) -> str | None:
    return _normalize_with_supported(provider, SUPPORTED_SPEND_LEDGER_PROVIDER_FILTERS)


def normalize_focus_export_provider_filter(provider: str | None) -> str | None:
    return _normalize_with_supported(provider, SUPPORTED_FOCUS_EXPORT_PROVIDER_FILTERS)


def _normalize_with_supported(
    provider: str | None,
    supported_providers: set[str],
) -> str | None:
    if provider is None:
        return None
    normalized = provider.strip().lower()
    if not normalized:
        return None
    if normalized not in supported_providers:
        supported = ", ".join(sorted(supported_providers))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider '{provider}'. Use one of: {supported}",
        )
    return normalized
