from __future__ import annotations

from pathlib import Path

import pytest

import scripts.verify_alembic_head_integrity as alembic_verifier
from scripts.verify_alembic_head_integrity import main, verify_alembic_heads


def _write_migration(
    base: Path,
    filename: str,
    *,
    revision: str,
    down_revision: str | tuple[str, ...] | None,
) -> None:
    if down_revision is None:
        down_literal = "None"
    elif isinstance(down_revision, tuple):
        quoted = ", ".join(repr(item) for item in down_revision)
        down_literal = f"({quoted},)"
    else:
        down_literal = repr(down_revision)

    content = (
        f"revision = {revision!r}\n"
        f"down_revision = {down_literal}\n"
        "branch_labels = None\n"
        "depends_on = None\n"
    )
    (base / filename).write_text(content, encoding="utf-8")


def test_verify_alembic_heads_passes_with_single_head(tmp_path: Path) -> None:
    versions = tmp_path / "versions"
    versions.mkdir(parents=True)
    _write_migration(versions, "001_initial.py", revision="001", down_revision=None)
    _write_migration(versions, "002_next.py", revision="002", down_revision="001")

    heads = verify_alembic_heads(versions)
    assert heads == ("002",)


def test_verify_alembic_heads_rejects_multiple_heads(tmp_path: Path) -> None:
    versions = tmp_path / "versions"
    versions.mkdir(parents=True)
    _write_migration(versions, "001_initial.py", revision="001", down_revision=None)
    _write_migration(versions, "002_branch_a.py", revision="002a", down_revision="001")
    _write_migration(versions, "003_branch_b.py", revision="002b", down_revision="001")

    with pytest.raises(RuntimeError, match="single-head policy violated"):
        verify_alembic_heads(versions)


def test_verify_alembic_heads_rejects_unknown_parent_reference(tmp_path: Path) -> None:
    versions = tmp_path / "versions"
    versions.mkdir(parents=True)
    _write_migration(versions, "001_initial.py", revision="001", down_revision=None)
    _write_migration(
        versions,
        "002_bad_parent.py",
        revision="002",
        down_revision="missing-parent",
    )

    with pytest.raises(RuntimeError, match="unknown parent revision"):
        verify_alembic_heads(versions)


def test_verify_alembic_heads_rejects_non_directory_migrations_path(tmp_path: Path) -> None:
    migrations_file = tmp_path / "versions.txt"
    migrations_file.write_text("not-a-directory\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Migrations path must be a directory"):
        verify_alembic_heads(migrations_file)


def test_main_resolves_relative_migrations_path_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    migrations_path = repo_root / "migrations" / "versions"
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(alembic_verifier, "_repo_root", lambda: repo_root)
    captured: dict[str, object] = {}

    def _fake_verify_alembic_heads(path: Path) -> tuple[str, ...]:
        captured["migrations_path"] = path
        return ("abc123",)

    monkeypatch.setattr(alembic_verifier, "verify_alembic_heads", _fake_verify_alembic_heads)

    assert main(["--migrations-path", "migrations/versions"]) == 0
    assert captured["migrations_path"] == migrations_path.resolve()


def test_main_rejects_relative_migrations_path_that_escapes_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(alembic_verifier, "_repo_root", lambda: repo_root)

    with pytest.raises(RuntimeError, match="migrations_path must stay within repo root when relative"):
        main(["--migrations-path", "../escape/versions"])
