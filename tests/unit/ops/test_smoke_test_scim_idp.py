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
