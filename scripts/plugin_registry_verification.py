"""Helpers for validating optimization plugin registration."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module

from app.modules.optimization.domain.registry import registry

REQUIRED_PLUGIN_CATEGORIES: dict[str, tuple[str, ...]] = {
    "aws": (
        "customer_managed_kms_keys",
        "idle_cloudfront_distributions",
        "idle_dynamodb_tables",
        "empty_efs_volumes",
    ),
    "azure": (
        "unattached_azure_disks",
        "orphan_azure_ips",
        "stopped_azure_vms",
    ),
    "gcp": (
        "unattached_gcp_disks",
        "stopped_gcp_instances",
    ),
}


@dataclass(frozen=True)
class ProviderVerificationResult:
    provider: str
    categories: tuple[str, ...]
    missing: tuple[str, ...]


def load_provider_plugins(provider: str) -> None:
    if provider == "aws":
        import_module("app.modules.optimization.adapters.aws.plugins")
        return

    if provider == "azure":
        azure_plugins = import_module("app.modules.optimization.adapters.azure.plugins")
        azure_plugins.load_plugins()
        return

    if provider == "gcp":
        gcp_plugins = import_module("app.modules.optimization.adapters.gcp.plugins")
        gcp_plugins.load_plugins()
        return

    raise ValueError(f"Unsupported provider: {provider}")


def collect_provider_categories(provider: str) -> tuple[str, ...]:
    return tuple(sorted({plugin.category_key for plugin in registry.get_plugins_for_provider(provider)}))


def verify_provider(provider: str) -> ProviderVerificationResult:
    required_categories = REQUIRED_PLUGIN_CATEGORIES.get(provider)
    if required_categories is None:
        raise ValueError(f"Unsupported provider: {provider}")

    load_provider_plugins(provider)
    categories = collect_provider_categories(provider)
    missing = tuple(category for category in required_categories if category not in categories)
    return ProviderVerificationResult(
        provider=provider,
        categories=categories,
        missing=missing,
    )


def verify_providers(
    providers: tuple[str, ...] = tuple(REQUIRED_PLUGIN_CATEGORIES)
) -> tuple[ProviderVerificationResult, ...]:
    return tuple(verify_provider(provider) for provider in providers)
