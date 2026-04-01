from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.smoke_test_scim_idp as scim_idp


def test_resolve_output_path_rejects_relative_repo_escape() -> None:
    with pytest.raises(SystemExit, match="out must stay within repo root when relative"):
        scim_idp.main(
            [
                "--scim-base-url",
                "https://example.com/scim/v2",
                "--scim-token",
                "token",
                "--out",
                "../escape.json",
            ]
        )


def test_resolve_output_path_rejects_directory(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    with pytest.raises(ValueError, match="out must be a file path"):
        scim_idp._resolve_output_path(str(output_dir))


def test_main_rejects_directory_output_before_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    monkeypatch.setattr(
        scim_idp,
        "_parse_args",
        lambda _argv=None: SimpleNamespace(
            scim_base_url="https://example.com/scim/v2",
            scim_token="token",
            idp="okta",
            write_mode=False,
            no_cleanup=False,
            timeout=15.0,
            out=str(output_dir),
            publish=False,
            api_url="http://127.0.0.1:8000",
        ),
    )

    with pytest.raises(SystemExit, match="out must be a file path"):
        scim_idp.main()


def test_main_uses_perf_counter_for_total_duration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    written: dict[str, object] = {}

    class DummyResponse:
        status_code = 200
        text = ""
        is_success = True

        def json(self):
            return {}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url: str):
            return DummyResponse()

    perf_values = iter([10.0, 10.1, 10.2, 10.3, 10.4])
    monkeypatch.setattr(scim_idp, "_perf_counter", lambda: next(perf_values))
    monkeypatch.setattr(scim_idp.httpx, "Client", DummyClient)
    monkeypatch.setattr(
        scim_idp,
        "_write_out",
        lambda _path, payload: written.update(payload),
    )

    exit_code = scim_idp.main(
        [
            "--scim-base-url",
            "https://example.com/scim/v2",
            "--scim-token",
            "token",
        ]
    )

    assert exit_code == 0
    assert written["duration_seconds"] == pytest.approx(0.4)
