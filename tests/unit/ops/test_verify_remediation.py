from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import scripts.verify_remediation as remediation_verifier


class _FakeForecaster:
    result = {
        "model": "symbolic",
        "total_forecasted_cost": Decimal("1000.50"),
    }

    @classmethod
    async def forecast(cls, history):
        assert len(history) == 10
        return cls.result


def test_verify_precision_returns_zero_for_decimal_result(
    monkeypatch,
) -> None:
    monkeypatch.setitem(
        __import__("sys").modules,
        "app.shared.analysis.forecaster",
        SimpleNamespace(SymbolicForecaster=_FakeForecaster),
    )

    assert remediation_verifier.main() == 0


def test_verify_precision_returns_one_for_missing_result_key(
    monkeypatch,
) -> None:
    class _MissingKeyForecaster:
        @classmethod
        async def forecast(cls, history):
            return {"model": "symbolic"}

    monkeypatch.setitem(
        __import__("sys").modules,
        "app.shared.analysis.forecaster",
        SimpleNamespace(SymbolicForecaster=_MissingKeyForecaster),
    )

    assert remediation_verifier.main() == 1


def test_verify_precision_returns_one_for_non_decimal_result(
    monkeypatch,
) -> None:
    class _BadTypeForecaster:
        @classmethod
        async def forecast(cls, history):
            return {
                "model": "symbolic",
                "total_forecasted_cost": 1000.5,
            }

    monkeypatch.setitem(
        __import__("sys").modules,
        "app.shared.analysis.forecaster",
        SimpleNamespace(SymbolicForecaster=_BadTypeForecaster),
    )

    assert remediation_verifier.main() == 1
