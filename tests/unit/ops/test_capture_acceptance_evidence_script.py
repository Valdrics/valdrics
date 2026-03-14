from __future__ import annotations

from pathlib import Path

import pytest

from scripts import capture_acceptance_evidence as script_module
from scripts.capture_acceptance_runner import CaptureResult


def test_normalize_base_url_handles_common_operator_inputs() -> None:
    assert script_module._normalize_base_url("127.0.0.1:8000") == "http://127.0.0.1:8000"
    assert script_module._normalize_base_url("localhost:8000") == "http://localhost:8000"
    assert script_module._normalize_base_url("valdrics.com") == "https://valdrics.com"
    assert script_module._normalize_base_url("https://valdrics.com") == "https://valdrics.com"


def test_main_requires_token_when_not_running_in_process(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VALDRICS_TOKEN", raising=False)
    with pytest.raises(
        SystemExit,
        match="Missing token. Set VALDRICS_TOKEN or pass --token",
    ):
        script_module.main(["--url", "http://127.0.0.1:8000", "--token", ""])


def test_main_uses_runner_capture_function(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    called: dict[str, object] = {}

    async def _fake_capture(**kwargs: object) -> tuple[Path, list[CaptureResult]]:
        called.update(kwargs)
        return (
            bundle_dir,
            [
                CaptureResult(
                    name="acceptance_kpis_json",
                    path="bundle/acceptance_kpis.json",
                    status_code=200,
                    ok=True,
                )
            ],
        )

    monkeypatch.setattr(script_module, "capture_acceptance_evidence", _fake_capture)

    exit_code = script_module.main(
        [
            "--url",
            "http://127.0.0.1:8000",
            "--token",
            "abc.def.ghi",
            "--output-root",
            str(tmp_path),
            "--start-date",
            "2026-01-01",
            "--end-date",
            "2026-01-31",
            "--close-start-date",
            "2025-12-01",
            "--close-end-date",
            "2025-12-31",
        ]
    )

    assert exit_code == 0
    assert called["base_url"] == "http://127.0.0.1:8000"
    assert called["output_root"] == tmp_path
    assert str(called["token"]) == "abc.def.ghi"


def test_main_returns_nonzero_when_bundle_is_incomplete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    async def _fake_capture(**_: object) -> tuple[Path, list[CaptureResult]]:
        return (
            bundle_dir,
            [
                CaptureResult(
                    name="acceptance_kpis_json",
                    path="bundle/acceptance_kpis.json",
                    status_code=200,
                    ok=True,
                ),
                CaptureResult(
                    name="acceptance_budget_summary_json",
                    path="bundle/acceptance_budget_summary.json",
                    status_code=500,
                    ok=False,
                    error="server error",
                ),
            ],
        )

    monkeypatch.setattr(script_module, "capture_acceptance_evidence", _fake_capture)

    exit_code = script_module.main(
        [
            "--url",
            "http://127.0.0.1:8000",
            "--token",
            "abc.def.ghi",
            "--output-root",
            str(tmp_path),
        ]
    )

    assert exit_code == 1
