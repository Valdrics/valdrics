from __future__ import annotations

from types import SimpleNamespace

import scripts.verify_activeops_e2e as activeops_verifier


def test_require_safe_environment_blocks_production_without_override(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        activeops_verifier,
        "get_settings",
        lambda: SimpleNamespace(ENVIRONMENT="production"),
    )
    monkeypatch.delenv("ALLOW_LIVE_VERIFICATION_MUTATIONS", raising=False)

    try:
        activeops_verifier._require_safe_environment()
    except RuntimeError as exc:
        assert "ALLOW_LIVE_VERIFICATION_MUTATIONS=true" in str(exc)
    else:
        raise AssertionError("Expected production safety gate to raise RuntimeError")


def test_require_safe_environment_allows_production_with_override(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        activeops_verifier,
        "get_settings",
        lambda: SimpleNamespace(ENVIRONMENT="production"),
    )
    monkeypatch.setenv("ALLOW_LIVE_VERIFICATION_MUTATIONS", "true")

    activeops_verifier._require_safe_environment()
