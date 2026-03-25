from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

import scripts.update_llm_pricing as update_llm_pricing


def test_main_returns_two_when_command_is_missing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert update_llm_pricing.main([]) == 2
    assert "Update LLM Provider Pricing" in capsys.readouterr().out


def test_main_rejects_negative_costs() -> None:
    with pytest.raises(SystemExit, match="--input and --output must be >= 0"):
        update_llm_pricing.main(
            ["update", "--provider", "openai", "--model", "gpt-5", "--input", "-1", "--output", "2"]
        )


def test_main_rejects_negative_free_tokens() -> None:
    with pytest.raises(SystemExit, match="--free must be >= 0"):
        update_llm_pricing.main(
            [
                "update",
                "--provider",
                "openai",
                "--model",
                "gpt-5",
                "--input",
                "1",
                "--output",
                "2",
                "--free",
                "-1",
            ]
        )


def test_main_runs_seed_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(update_llm_pricing, "seed_from_static_data", AsyncMock())

    assert update_llm_pricing.main(["seed"]) == 0
    update_llm_pricing.seed_from_static_data.assert_awaited_once()


def test_main_runs_update_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(update_llm_pricing, "update_pricing", AsyncMock())

    assert (
        update_llm_pricing.main(
            [
                "update",
                "--provider",
                "openai",
                "--model",
                "gpt-5",
                "--input",
                "1",
                "--output",
                "2",
                "--free",
                "3",
            ]
        )
        == 0
    )
    update_llm_pricing.update_pricing.assert_awaited_once_with("openai", "gpt-5", 1.0, 2.0, 3)
