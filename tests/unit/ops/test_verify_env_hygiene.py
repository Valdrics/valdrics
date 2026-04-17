from __future__ import annotations

import os
from pathlib import Path

import pytest

import scripts.verify_env_hygiene as env_hygiene_verifier
from scripts.verify_env_hygiene import main, verify_env_hygiene


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _valid_template() -> str:
    return "\n".join(
        [
            'APP_NAME="Valdrics"',
            "CSRF_SECRET_KEY=",
            "SMTP_USER=",
            "CLOUDFORMATION_TEMPLATE_URL=",
            "DB_POOL_SIZE=20",
            "DB_MAX_OVERFLOW=10",
            "DB_POOL_TIMEOUT=30",
        ]
    )


def test_verify_env_hygiene_passes_for_hardened_template(
    tmp_path: Path, monkeypatch
) -> None:
    _write(tmp_path / ".env.example", _valid_template())
    monkeypatch.setattr(
        "scripts.verify_env_hygiene._tracked_env_files",
        lambda _repo_root: (),
    )

    errors = verify_env_hygiene(
        repo_root=tmp_path,
        template_path=Path(".env.example"),
    )

    assert errors == ()


def test_verify_env_hygiene_flags_tracked_env_and_secret_values(
    tmp_path: Path, monkeypatch
) -> None:
    _write(
        tmp_path / ".env.example",
        "\n".join(
            [
                'APP_NAME="Valdrix"',
                "CSRF_SECRET_KEY=super-secret",
                "SMTP_USER=deeprince2020@gmail.com",
                "CLOUDFORMATION_TEMPLATE_URL=https://valdrix-templates.example.com",
                "DB_POOL_SIZE=0",
                "DB_MAX_OVERFLOW=abc",
            ]
        ),
    )
    monkeypatch.setattr(
        "scripts.verify_env_hygiene._tracked_env_files",
        lambda _repo_root: (".env", "dashboard/.env"),
    )

    errors = verify_env_hygiene(
        repo_root=tmp_path,
        template_path=Path(".env.example"),
    )
    joined = "\n".join(errors)

    assert "`.env` is tracked by git" in joined
    assert "`dashboard/.env` is tracked by git" in joined
    assert "APP_NAME in .env.example must be exactly `Valdrics`" in joined
    assert "CSRF_SECRET_KEY in .env.example must be empty." in joined
    assert "SMTP_USER in .env.example must be empty." in joined
    assert "forbidden personal email domain: gmail.com" in joined
    assert "old `valdrix` branding" in joined
    assert "DB_POOL_SIZE=0" in joined
    assert "DB_MAX_OVERFLOW='abc'" in joined
    assert "Missing required key in .env.example: DB_POOL_TIMEOUT" in joined


def test_verify_env_hygiene_flags_retired_managed_runtime_keys(
    tmp_path: Path, monkeypatch
) -> None:
    _write(
        tmp_path / ".env.example",
        "\n".join(
            [
                _valid_template(),
                "REDIS_URL=redis://localhost:6379/0",
                "UPSTASH_REDIS_URL=https://example.upstash.io",
                "UPSTASH_REDIS_TOKEN=secret",
                "CIRCUIT_BREAKER_DISTRIBUTED_STATE=true",
                "CIRCUIT_BREAKER_DISTRIBUTED_KEY_PREFIX=valdrics:circuit",
                "SENTRY_DSN=https://example@sentry.io/1",
                "OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.example.com",
                "OTEL_LOGS_EXPORT_ENABLED=true",
            ]
        ),
    )
    monkeypatch.setattr(
        "scripts.verify_env_hygiene._tracked_env_files",
        lambda _repo_root: (),
    )

    errors = verify_env_hygiene(
        repo_root=tmp_path,
        template_path=Path(".env.example"),
    )

    joined = "\n".join(errors)
    assert "Retired managed-runtime key must not appear in .env.example: REDIS_URL" in joined
    assert "Retired managed-runtime key must not appear in .env.example: UPSTASH_REDIS_URL" in joined
    assert "Retired managed-runtime key must not appear in .env.example: UPSTASH_REDIS_TOKEN" in joined
    assert (
        "Retired managed-runtime key must not appear in .env.example: CIRCUIT_BREAKER_DISTRIBUTED_STATE"
        in joined
    )
    assert (
        "Retired managed-runtime key must not appear in .env.example: CIRCUIT_BREAKER_DISTRIBUTED_KEY_PREFIX"
        in joined
    )
    assert "Retired managed-runtime key must not appear in .env.example: SENTRY_DSN" in joined
    assert (
        "Retired managed-runtime key must not appear in .env.example: OTEL_EXPORTER_OTLP_ENDPOINT"
        in joined
    )
    assert (
        "Retired managed-runtime key must not appear in .env.example: OTEL_LOGS_EXPORT_ENABLED"
        in joined
    )


def test_main_returns_failure_for_missing_template(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.verify_env_hygiene._tracked_env_files",
        lambda _repo_root: (),
    )

    exit_code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--template-path",
            ".env.example",
        ]
    )

    assert exit_code == 1


def test_verify_env_hygiene_rejects_non_directory_repo_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo-root"
    repo_root.write_text("not-a-directory", encoding="utf-8")

    errors = verify_env_hygiene(
        repo_root=repo_root,
        template_path=Path(".env.example"),
    )

    assert errors == (f"repo_root must be a directory: {repo_root.as_posix()}",)


def test_verify_env_hygiene_rejects_relative_template_repo_escape(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    errors = verify_env_hygiene(
        repo_root=repo_root,
        template_path=Path("../outside.env"),
    )

    assert errors == ("template_path must stay within repo root when relative",)


def test_verify_env_hygiene_rejects_directory_template_path(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    template_dir = repo_root / ".env.example"
    template_dir.mkdir()

    errors = verify_env_hygiene(
        repo_root=repo_root,
        template_path=Path(".env.example"),
    )

    assert errors == (f"Template path must be a file: {template_dir}",)


def test_main_resolves_relative_template_path_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    template_path = repo_root / ".env.example"
    _write(template_path, _valid_template())

    monkeypatch.setattr(
        "scripts.verify_env_hygiene._tracked_env_files",
        lambda _repo_root: (),
    )

    old_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        exit_code = main(
            [
                "--repo-root",
                str(repo_root),
                "--template-path",
                ".env.example",
            ]
        )
    finally:
        os.chdir(old_cwd)

    assert exit_code == 0


def test_main_resolves_relative_repo_root_from_repo_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(env_hygiene_verifier.__file__).resolve().parents[1]
    captured: dict[str, Path] = {}

    def _capture(*, repo_root: Path, template_path: Path) -> tuple[str, ...]:
        captured["repo_root"] = repo_root
        captured["template_path"] = template_path
        return ()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(env_hygiene_verifier, "verify_env_hygiene", _capture)

    assert main(["--repo-root", ".", "--template-path", ".env.example"]) == 0
    assert captured["repo_root"] == repo_root
    assert captured["template_path"] == Path(".env.example")


def test_main_rejects_relative_repo_root_repo_escape() -> None:
    assert main(["--repo-root", os.path.join("..", "..")]) == 2
