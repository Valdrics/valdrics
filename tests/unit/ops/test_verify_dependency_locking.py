from __future__ import annotations

from pathlib import Path

import pytest

import scripts.verify_dependency_locking as dependency_locking
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
                'dependencies = ["fastapi~=0.128.0"]',
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
                "      - uses: astral-sh/setup-uv@v5",
                "        with:",
                '          version: "${{ env.UV_VERSION }}"',
                "      - run: uv sync --locked --dev",
            ]
        ),
    )
    _write(
        tmp_path / "Dockerfile",
        "\n".join(
            [
                "FROM python:3.12-slim",
                "ARG UV_VERSION=0.9.21",
                'RUN pip install --no-cache-dir "uv==${UV_VERSION}"',
                "COPY pyproject.toml uv.lock ./",
                "RUN uv sync --frozen --no-dev --no-install-project",
                "COPY app ./app",
                "RUN uv sync --frozen --no-dev",
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
                "      - uses: astral-sh/setup-uv@v5",
                "        with:",
                '          version: "0.9.21"',
                "      - run: uv sync --locked --dev",
            ]
        ),
    )

    errors = verify_dependency_locking(repo_root=tmp_path)
    assert any("lockfile missing" in item for item in errors)
    assert any("critical dependencies must use bounded compatibility" in item for item in errors)


def test_verify_dependency_locking_allows_noncritical_open_ended_with_lockfile(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "pyproject.toml",
        "\n".join(
            [
                "[project]",
                'name = "demo"',
                'version = "0.1.0"',
                'dependencies = ["boto3>=1.36.20"]',
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
                "      - uses: astral-sh/setup-uv@v5",
                "        with:",
                '          version: "0.9.21"',
                "      - run: uv sync --locked --dev",
            ]
        ),
    )
    _write(
        tmp_path / "Dockerfile",
        "\n".join(
            [
                "FROM python:3.12-slim",
                "ARG UV_VERSION=0.9.21",
                'RUN pip install --no-cache-dir "uv==${UV_VERSION}"',
                "COPY pyproject.toml uv.lock ./",
                "RUN uv sync --frozen --no-dev",
            ]
        ),
    )

    errors = verify_dependency_locking(repo_root=tmp_path)
    assert errors == ()


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
                'dependencies = ["fastapi~=0.128.0"]',
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
                "      - uses: astral-sh/setup-uv@v5",
                "        with:",
                '          version: "0.9.21"',
                "      - run: uv sync --dev",
            ]
        ),
    )

    errors = verify_dependency_locking(repo_root=tmp_path)
    assert any("workflow install must be lock-enforced" in item for item in errors)


def test_main_returns_failure_for_missing_pyproject(tmp_path: Path) -> None:
    exit_code = main(["--repo-root", str(tmp_path)])
    assert exit_code == 1


def test_verify_dependency_locking_flags_latest_setup_uv_channel(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        "\n".join(
            [
                "[project]",
                'name = "demo"',
                'version = "0.1.0"',
                'dependencies = ["fastapi~=0.128.0"]',
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
                "      - uses: astral-sh/setup-uv@v5",
                "        with:",
                '          version: "latest"',
                "      - run: uv sync --locked --dev",
            ]
        ),
    )
    _write(
        tmp_path / "Dockerfile",
        "\n".join(
            [
                "FROM python:3.12-slim",
                "ARG UV_VERSION=0.9.21",
                'RUN pip install --no-cache-dir "uv==${UV_VERSION}"',
                "COPY pyproject.toml uv.lock ./",
                "RUN uv sync --frozen --no-dev",
            ]
        ),
    )

    errors = verify_dependency_locking(repo_root=tmp_path)
    assert any("must not use the mutable `latest` channel" in item for item in errors)


def test_verify_dependency_locking_flags_dockerfile_that_skips_lockfile(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        "\n".join(
            [
                "[project]",
                'name = "demo"',
                'version = "0.1.0"',
                'dependencies = ["fastapi~=0.128.0"]',
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
                "      - uses: astral-sh/setup-uv@v5",
                "        with:",
                '          version: "0.9.21"',
                "      - run: uv sync --locked --dev",
            ]
        ),
    )
    _write(
        tmp_path / "Dockerfile",
        "\n".join(
            [
                "FROM python:3.12-slim",
                "RUN pip install --no-cache-dir uv",
                "COPY pyproject.toml uv.lock ./",
                "RUN uv pip install --no-cache -r pyproject.toml",
            ]
        ),
    )

    errors = verify_dependency_locking(repo_root=tmp_path)
    assert any("must install a pinned uv release" in item for item in errors)
    assert any("must not bypass the lockfile" in item for item in errors)


def test_verify_dependency_locking_rejects_non_directory_repo_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo-root.txt"
    repo_root.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ValueError, match="repo_root must be a directory"):
        verify_dependency_locking(repo_root=repo_root)


def test_main_resolves_default_repo_root_from_script_location(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[Path] = []
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(dependency_locking, "_repo_root", lambda: repo)
    monkeypatch.setattr(
        dependency_locking,
        "verify_dependency_locking",
        lambda *, repo_root, pyproject_path, lock_path, workflows_root, dockerfile_paths: seen.append(repo_root) or (),
    )

    assert main([]) == 0
    assert seen == [repo]


def test_main_rejects_relative_path_escape(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    assert main(["--repo-root", str(repo_root), "--pyproject-path", "../escape/pyproject.toml"]) == 2


def test_main_rejects_directory_pyproject_path(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    pyproject_dir = repo_root / "pyproject.toml"
    pyproject_dir.mkdir()

    assert main(["--repo-root", str(repo_root), "--pyproject-path", "pyproject.toml"]) == 2
