from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts import plugin_registry_verification, verify_all_plugins, verify_plugins


def test_load_provider_plugins_dispatches_for_aws(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake_import_module(module_name: str) -> object:
        seen.append(module_name)
        return object()

    monkeypatch.setattr(plugin_registry_verification, "import_module", fake_import_module)

    plugin_registry_verification.load_provider_plugins("aws")

    assert seen == ["app.modules.optimization.adapters.aws.plugins"]


def test_verify_provider_loads_plugins_before_collecting_categories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    categories: list[str] = []
    fake_registry = SimpleNamespace(
        get_plugins_for_provider=lambda provider: [
            SimpleNamespace(category_key=category) for category in categories
        ]
    )

    def fake_load(provider: str) -> None:
        assert provider == "aws"
        categories[:] = [
            "customer_managed_kms_keys",
            "idle_cloudfront_distributions",
            "idle_dynamodb_tables",
            "empty_efs_volumes",
        ]

    monkeypatch.setattr(plugin_registry_verification, "registry", fake_registry)
    monkeypatch.setattr(plugin_registry_verification, "load_provider_plugins", fake_load)

    result = plugin_registry_verification.verify_provider("aws")

    assert result.categories == (
        "customer_managed_kms_keys",
        "empty_efs_volumes",
        "idle_cloudfront_distributions",
        "idle_dynamodb_tables",
    )
    assert result.missing == ()


def test_verify_plugins_main_fails_when_required_aws_categories_are_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        verify_plugins,
        "verify_provider",
        lambda provider: plugin_registry_verification.ProviderVerificationResult(
            provider=provider,
            categories=("customer_managed_kms_keys",),
            missing=("idle_cloudfront_distributions",),
        ),
    )

    assert verify_plugins.main() == 1
    assert "idle_cloudfront_distributions" in capsys.readouterr().out


def test_verify_all_plugins_main_returns_success_when_all_providers_are_registered(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        verify_all_plugins,
        "verify_providers",
        lambda: (
            plugin_registry_verification.ProviderVerificationResult(
                provider="aws",
                categories=("customer_managed_kms_keys",),
                missing=(),
            ),
            plugin_registry_verification.ProviderVerificationResult(
                provider="azure",
                categories=("stopped_azure_vms",),
                missing=(),
            ),
            plugin_registry_verification.ProviderVerificationResult(
                provider="gcp",
                categories=("stopped_gcp_instances",),
                missing=(),
            ),
        ),
    )

    assert verify_all_plugins.main() == 0
    assert "SUCCESS" in capsys.readouterr().out
