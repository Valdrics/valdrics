from __future__ import annotations

import os
from pathlib import Path

import scripts.verify_enterprise_placeholder_guards as placeholder_verifier
from scripts.verify_enterprise_placeholder_guards import (
    DEFAULT_FULL_SCAN_ROOTS,
    DEFAULT_MARKER_PATTERNS,
    DEFAULT_STRICT_SCAN_ROOTS,
    _resolve_scan_roots,
    load_allow_rules,
    main,
    scan_paths_for_disallowed_markers,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_scan_paths_for_disallowed_markers_detects_forbidden_tokens(tmp_path: Path) -> None:
    _write(tmp_path / "safe.py", "def ok() -> int:\n    return 1\n")
    _write(tmp_path / "bad.py", "# TODO: remove\nraise NotImplementedError()\n")

    violations = scan_paths_for_disallowed_markers(
        roots=[tmp_path],
        marker_patterns=DEFAULT_MARKER_PATTERNS,
    )

    assert violations
    assert any(item.path.endswith("bad.py") for item in violations)
    assert any("TODO" in item.matched_text for item in violations)


def test_scan_paths_for_disallowed_markers_ignores_non_python_files(tmp_path: Path) -> None:
    _write(tmp_path / "readme.txt", "TODO: docs note only\n")

    violations = scan_paths_for_disallowed_markers(
        roots=[tmp_path],
        marker_patterns=DEFAULT_MARKER_PATTERNS,
    )

    assert violations == []


def test_scan_paths_respects_allow_rules(tmp_path: Path) -> None:
    _write(tmp_path / "bad.py", "# TODO: keep for test\nraise NotImplementedError()\n")
    allowlist = tmp_path / "allowlist.txt"
    _write(allowlist, r"^.*bad\.py$::TODO")

    rules = load_allow_rules(allowlist)
    violations = scan_paths_for_disallowed_markers(
        roots=[tmp_path],
        marker_patterns=DEFAULT_MARKER_PATTERNS,
        allow_rules=rules,
    )

    # TODO marker is ignored by allowlist, but NotImplementedError remains.
    assert len(violations) == 1
    assert violations[0].matched_text == "NotImplementedError"


def test_resolve_scan_roots_uses_profile_defaults() -> None:
    assert _resolve_scan_roots("strict", []) == tuple(
        placeholder_verifier._resolve_repo_path(path) for path in DEFAULT_STRICT_SCAN_ROOTS
    )
    assert _resolve_scan_roots("full", []) == tuple(
        placeholder_verifier._resolve_repo_path(path) for path in DEFAULT_FULL_SCAN_ROOTS
    )


def test_main_resolves_relative_roots_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    target = repo_root / "app/modules/enforcement/sample.py"
    _write(target, "def ok() -> int:\n    return 1\n")
    monkeypatch.setattr(placeholder_verifier, "_repo_root", lambda: repo_root)

    old_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        exit_code = main(["--root", "app/modules/enforcement"])
    finally:
        os.chdir(old_cwd)

    assert exit_code == 0


def test_main_rejects_relative_root_repo_escape(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setattr(placeholder_verifier, "_repo_root", lambda: repo_root)

    assert main(["--root", "../escape/app"]) == 2
