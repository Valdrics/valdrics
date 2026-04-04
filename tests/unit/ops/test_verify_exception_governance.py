from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import scripts.verify_exception_governance as exception_governance_verifier
from scripts.verify_exception_governance import (
    ExceptionSite,
    collect_exception_sites,
    main,
    verify_against_baseline,
    write_baseline,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_collect_exception_sites_detects_catch_all_variants(tmp_path: Path) -> None:
    root = tmp_path / "code"
    _write(
        root / "a.py",
        "\n".join(
            [
                "try:",
                "    raise RuntimeError('x')",
                "except Exception:",
                "    pass",
                "try:",
                "    raise RuntimeError('y')",
                "except (ValueError, Exception):",
                "    pass",
                "try:",
                "    raise RuntimeError('z')",
                "except:",
                "    pass",
            ]
        ),
    )

    sites = collect_exception_sites(roots=(root,))
    assert [site.kind for site in sites] == [
        "exception",
        "tuple_exception",
        "bare_except",
    ]


def test_verify_against_baseline_reports_added_and_bare() -> None:
    baseline = (ExceptionSite(path="app/x.py", line=10, kind="exception"),)
    current = baseline + (
        ExceptionSite(path="app/y.py", line=20, kind="tuple_exception"),
        ExceptionSite(path="app/z.py", line=30, kind="bare_except"),
    )
    added, removed, bare = verify_against_baseline(current=current, baseline=baseline)

    assert [site.key() for site in added] == [
        "app/y.py:20:tuple_exception",
        "app/z.py:30:bare_except",
    ]
    assert removed == ()
    assert [site.key() for site in bare] == ["app/z.py:30:bare_except"]


def test_main_write_baseline_and_verify_roundtrip(tmp_path: Path) -> None:
    root = tmp_path / "code"
    baseline_path = tmp_path / "baseline.json"
    _write(
        root / "sample.py",
        "\n".join(
            [
                "def f():",
                "    try:",
                "        return 1",
                "    except Exception as exc:",
                "        return str(exc)",
            ]
        ),
    )

    write_exit = main(
        [
            "--root",
            str(root),
            "--baseline-path",
            str(baseline_path),
            "--write-baseline",
        ]
    )
    assert write_exit == 0
    raw = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert raw["sites"][0]["kind"] == "exception"

    verify_exit = main(
        [
            "--root",
            str(root),
            "--baseline-path",
            str(baseline_path),
        ]
    )
    assert verify_exit == 0


def test_write_baseline_serializes_repo_roots_relative(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    root = repo_root / "app"
    baseline_path = repo_root / "docs" / "ops" / "evidence" / "baseline.json"
    _write(
        root / "sample.py",
        "\n".join(
            [
                "def f():",
                "    try:",
                "        return 1",
                "    except Exception as exc:",
                "        return str(exc)",
            ]
        ),
    )
    monkeypatch.setattr(exception_governance_verifier, "_repo_root", lambda: repo_root)

    sites = collect_exception_sites(roots=(root,))
    write_baseline(baseline_path=baseline_path, roots=(root,), sites=sites)

    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert payload["roots"] == ["app"]


def test_repo_baseline_matches_current_exception_sites() -> None:
    exit_code = main(
        [
            "--root",
            str(REPO_ROOT / "app"),
            "--root",
            str(REPO_ROOT / "scripts"),
            "--baseline-path",
            str(REPO_ROOT / "docs/ops/evidence/exception_governance_baseline.json"),
        ]
    )
    assert exit_code == 0


def test_main_write_baseline_does_not_leave_output_when_promotion_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "code"
    baseline_path = tmp_path / "baseline.json"
    path_type = type(baseline_path)
    original_replace = path_type.replace
    _write(
        root / "sample.py",
        "\n".join(
            [
                "def f():",
                "    try:",
                "        return 1",
                "    except Exception as exc:",
                "        return str(exc)",
            ]
        ),
    )

    def _failing_replace(self: Path, target: Path) -> Path:
        if self.parent == baseline_path.parent and Path(target) == baseline_path:
            raise OSError("simulated promotion failure")
        return original_replace(self, target)

    monkeypatch.setattr(path_type, "replace", _failing_replace)

    with pytest.raises(OSError, match="simulated promotion failure"):
        main(
            [
                "--root",
                str(root),
                "--baseline-path",
                str(baseline_path),
                "--write-baseline",
            ]
        )

    assert not baseline_path.exists()
    assert not list(baseline_path.parent.glob(f".{baseline_path.stem}.*{baseline_path.suffix}.tmp"))


def test_main_resolves_default_roots_and_baseline_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(exception_governance_verifier.__file__).resolve().parents[1]
    captured: dict[str, object] = {}

    def _capture_sites(*, roots: tuple[Path, ...]) -> tuple[ExceptionSite, ...]:
        captured["roots"] = roots
        return ()

    def _capture_write(
        *,
        baseline_path: Path,
        roots: tuple[Path, ...],
        sites: tuple[ExceptionSite, ...],
    ) -> None:
        captured["baseline_path"] = baseline_path
        captured["write_roots"] = roots

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        exception_governance_verifier,
        "collect_exception_sites",
        _capture_sites,
    )
    monkeypatch.setattr(
        exception_governance_verifier,
        "write_baseline",
        _capture_write,
    )

    assert main(["--write-baseline"]) == 0
    assert captured["roots"] == (repo_root / "app", repo_root / "scripts")
    assert captured["write_roots"] == (repo_root / "app", repo_root / "scripts")
    assert captured["baseline_path"] == (
        repo_root / "docs" / "ops" / "evidence" / "exception_governance_baseline.json"
    )


def test_main_rejects_relative_root_repo_escape() -> None:
    assert main(["--root", os.path.join("..", ".."), "--write-baseline"]) == 2


def test_main_rejects_relative_baseline_repo_escape() -> None:
    assert (
        main(
            [
                "--root",
                str(REPO_ROOT / "app"),
                "--baseline-path",
                os.path.join("..", "outside.json"),
                "--write-baseline",
            ]
        )
        == 2
    )
