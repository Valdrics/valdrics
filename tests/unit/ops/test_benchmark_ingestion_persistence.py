from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.benchmark_ingestion_persistence as benchmark_script


def test_resolve_output_path_rejects_relative_repo_escape() -> None:
    with pytest.raises(ValueError, match="out must stay within repo root when relative"):
        benchmark_script._resolve_output_path("../outside.json")


def test_resolve_output_path_rejects_directory(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    with pytest.raises(ValueError, match="out must be a file path"):
        benchmark_script._resolve_output_path(str(output_dir))


def test_write_output_stages_before_promotion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "benchmark.json"
    staged_path = tmp_path / ".benchmark.json.tmp"

    def _fake_stage(path: Path, payload: object, **_: object) -> Path:
        assert path == output_path
        staged_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return staged_path

    def _fake_promote(staged: Path, output: Path) -> None:
        staged.replace(output)

    monkeypatch.setattr(benchmark_script, "stage_json_file", _fake_stage)
    monkeypatch.setattr(benchmark_script, "promote_staged_file", _fake_promote)

    benchmark_script._write_output(output_path, {"ok": True})

    assert json.loads(output_path.read_text(encoding="utf-8"))["ok"] is True


@pytest.mark.asyncio
async def test_main_rejects_directory_output_before_db_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    monkeypatch.setattr(
        benchmark_script,
        "_parse_args",
        lambda _argv=None: SimpleNamespace(
            url="http://127.0.0.1:8000",
            records=10,
            services=2,
            regions=2,
            min_rps=None,
            backfill_runs=0,
            min_backfill_rps=None,
            provider="aws",
            tenant_id="",
            account_id="",
            no_cleanup=False,
            out=str(output_dir),
            publish=False,
        ),
    )

    with pytest.raises(SystemExit, match="out must be a file path"):
        await benchmark_script.main()
