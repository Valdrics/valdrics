from __future__ import annotations

from pathlib import Path

from scripts.verify_dependency_locking import main, verify_dependency_locking


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_verify_dependency_locking_passes_with_locked_workflow_and_lockfile(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "pyproject.toml",
        "\n".join(
            [
                "[project]",
                'name = "demo"',
                'version = "0.1.0"',
                'dependencies = ["fastapi>=0.128.0"]',
            ]
        ),
    )
    _write(tmp_path / "uv.lock", "version = 1\n")
    _write(
        tmp_path / ".github/workflows/ci.yml",
        "\n".join(
            [
                "jobs:",
                "  test:",
                "    steps:",
                "      - run: uv sync --locked --dev",
            ]
        ),
    )

    errors = verify_dependency_locking(repo_root=tmp_path)
    assert errors == ()


def test_verify_dependency_locking_flags_open_ended_spec_without_lockfile(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "pyproject.toml",
        "\n".join(
            [
                "[project]",
                'name = "demo"',
                'version = "0.1.0"',
                'dependencies = ["sqlalchemy>=2.0.0"]',
            ]
        ),
    )
    _write(
        tmp_path / ".github/workflows/ci.yml",
        "\n".join(
            [
                "jobs:",
                "  test:",
                "    steps:",
                "      - run: uv sync --locked --dev",
            ]
        ),
    )

    errors = verify_dependency_locking(repo_root=tmp_path)
    assert any("lockfile missing" in item for item in errors)


def test_verify_dependency_locking_flags_unlocked_uv_sync_command(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "pyproject.toml",
        "\n".join(
            [
                "[project]",
                'name = "demo"',
                'version = "0.1.0"',
                'dependencies = ["fastapi>=0.128.0"]',
            ]
        ),
    )
    _write(tmp_path / "uv.lock", "version = 1\n")
    _write(
        tmp_path / ".github/workflows/ci.yml",
        "\n".join(
            [
                "jobs:",
                "  test:",
                "    steps:",
                "      - run: uv sync --dev",
            ]
        ),
    )

    errors = verify_dependency_locking(repo_root=tmp_path)
    assert any("workflow install must be lock-enforced" in item for item in errors)


def test_main_returns_failure_for_missing_pyproject(tmp_path: Path) -> None:
    exit_code = main(["--repo-root", str(tmp_path)])
    assert exit_code == 1

