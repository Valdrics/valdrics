from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.generate_managed_migration_env as managed_migration_env_generator
from scripts.generate_managed_migration_env import generate_managed_migration_env


def _parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def test_generate_managed_migration_env_defaults_to_database_url_blocker(
    tmp_path: Path,
) -> None:
    output = tmp_path / "production.migrate.env"
    report_path = tmp_path / "production.migrate.report.json"

    report = generate_managed_migration_env(
        output_path=output,
        report_path=report_path,
        environment="production",
    )
    values = _parse_env(output)
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert values["ENVIRONMENT"] == "production"
    assert values["DB_SSL_MODE"] == "require"
    assert values["DATABASE_URL"].startswith("postgresql+asyncpg://REPLACE_WITH_DB_USER")
    assert report["migration_ready"] is False
    assert report_payload["required_operator_input_keys"] == ["DATABASE_URL"]
    assert report_payload["migration_validation_blockers"] == ["DATABASE_URL"]


def test_generate_managed_migration_env_requires_ca_path_for_verified_ssl(
    tmp_path: Path,
) -> None:
    output = tmp_path / "staging.migrate.env"
    report_path = tmp_path / "staging.migrate.report.json"

    generate_managed_migration_env(
        output_path=output,
        report_path=report_path,
        environment="staging",
        database_url="postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
        db_ssl_mode="verify-full",
    )
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert report_payload["required_operator_input_keys"] == [
        "DATABASE_URL",
        "DB_SSL_CA_CERT_PATH",
    ]
    assert report_payload["migration_validation_blockers"] == ["DB_SSL_CA_CERT_PATH"]


def test_generate_managed_migration_env_treats_placeholder_ca_path_as_blocker(
    tmp_path: Path,
) -> None:
    output = tmp_path / "staging.migrate.env"
    report_path = tmp_path / "staging.migrate.report.json"

    generate_managed_migration_env(
        output_path=output,
        report_path=report_path,
        environment="staging",
        database_url="postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
        db_ssl_mode="verify-ca",
        db_ssl_ca_cert_path="REPLACE_WITH_DB_CA_CERT_PATH",
    )
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert report_payload["migration_validation_blockers"] == ["DB_SSL_CA_CERT_PATH"]


def test_generate_managed_migration_env_rejects_shared_output_and_report_path(
    tmp_path: Path,
) -> None:
    combined = tmp_path / "staging.migrate.env"

    with pytest.raises(ValueError, match="output_path and report_path must be different files"):
        generate_managed_migration_env(
            output_path=combined,
            report_path=combined,
            environment="staging",
        )


def test_generate_managed_migration_env_does_not_leave_outputs_when_report_staging_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "staging.migrate.env"
    report_path = tmp_path / "staging.migrate.report.json"
    original_stage = managed_migration_env_generator._stage_text_file

    def _failing_stage(path: Path, content: str) -> Path:
        if path == report_path:
            raise RuntimeError("report staging failed")
        return original_stage(path, content)

    monkeypatch.setattr(
        managed_migration_env_generator,
        "_stage_text_file",
        _failing_stage,
    )

    with pytest.raises(RuntimeError, match="report staging failed"):
        generate_managed_migration_env(
            output_path=output,
            report_path=report_path,
            environment="staging",
        )

    assert not output.exists()
    assert not report_path.exists()


@pytest.mark.parametrize("field_name", ["output_path", "report_path"])
def test_generate_managed_migration_env_rejects_directory_targets(
    tmp_path: Path,
    field_name: str,
) -> None:
    output = tmp_path / "staging.migrate.env"
    report_path = tmp_path / "staging.migrate.report.json"
    bad_target = tmp_path / field_name
    bad_target.mkdir()

    kwargs = {
        "output_path": output,
        "report_path": report_path,
        "environment": "staging",
    }
    kwargs[field_name] = bad_target

    with pytest.raises(ValueError, match=rf"{field_name} must be a file path"):
        generate_managed_migration_env(**kwargs)


@pytest.mark.parametrize("field_name", ["output_path", "report_path"])
def test_generate_managed_migration_env_rejects_blocked_parent_dirs(
    tmp_path: Path,
    field_name: str,
) -> None:
    blocked_parent = tmp_path / f"blocked-{field_name}"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")
    safe_parent = tmp_path / "safe-parent"
    kwargs = {
        "output_path": safe_parent / "staging.migrate.env",
        "report_path": safe_parent / "staging.migrate.report.json",
        "environment": "staging",
    }
    kwargs[field_name] = blocked_parent / Path(kwargs[field_name]).name

    with pytest.raises(ValueError, match=rf"{field_name} parent must be a directory path"):
        generate_managed_migration_env(**kwargs)


def test_main_resolves_default_paths_from_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def _fake_generate_managed_migration_env(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        output_path = kwargs["output_path"]
        return {
            "environment": kwargs["environment"],
            "output_path": output_path.as_posix(),
            "migration_ready": False,
            "migration_validation_blockers": [],
        }

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        managed_migration_env_generator,
        "generate_managed_migration_env",
        _fake_generate_managed_migration_env,
    )

    assert managed_migration_env_generator.main(["--environment", "staging"]) == 0
    assert captured["output_path"] == (
        managed_migration_env_generator._repo_root()
        / managed_migration_env_generator.DEFAULT_OUTPUT_DIR
        / "staging.migrate.env"
    ).resolve()
    assert captured["report_path"] == (
        managed_migration_env_generator._repo_root()
        / managed_migration_env_generator.DEFAULT_OUTPUT_DIR
        / "staging.migrate.report.json"
    ).resolve()


def test_main_resolves_explicit_relative_paths_from_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    captured: dict[str, object] = {}

    def _fake_generate_managed_migration_env(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        output_path = kwargs["output_path"]
        return {
            "environment": kwargs["environment"],
            "output_path": output_path.as_posix(),  # type: ignore[index]
            "migration_ready": False,
            "migration_validation_blockers": [],
        }

    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(managed_migration_env_generator, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(
        managed_migration_env_generator,
        "generate_managed_migration_env",
        _fake_generate_managed_migration_env,
    )

    assert (
        managed_migration_env_generator.main(
            [
                "--environment",
                "staging",
                "--output-path",
                ".runtime/staging.migrate.env",
                "--report-path",
                ".runtime/staging.migrate.report.json",
            ]
        )
        == 0
    )
    assert captured["output_path"] == (
        repo_root / ".runtime" / "staging.migrate.env"
    ).resolve()
    assert captured["report_path"] == (
        repo_root / ".runtime" / "staging.migrate.report.json"
    ).resolve()


def test_main_rejects_relative_paths_that_escape_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)

    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(managed_migration_env_generator, "_repo_root", lambda: repo_root)

    with pytest.raises(ValueError, match="output_path must stay within repo root when relative"):
        managed_migration_env_generator.main(
            [
                "--environment",
                "staging",
                "--output-path",
                "../escape/staging.migrate.env",
            ]
        )


@pytest.mark.parametrize(
    ("field_name", "relative_target"),
    [
        ("output_path", ".env.example"),
        ("report_path", "scripts/validate_migration_env.py"),
        ("output_path", "docs/ops/evidence/finance_telemetry_snapshot_TEMPLATE.json"),
        ("report_path", "docs/ops/feature_enforceability_matrix_2026-02-27.json"),
        ("output_path", "docs/ops/evidence/README.md"),
    ],
)
def test_generate_managed_migration_env_rejects_protected_output_targets(
    field_name: str,
    relative_target: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    kwargs = {
        "output_path": repo_root / "tmp-staging.migrate.env",
        "report_path": repo_root / "tmp-staging.migrate.report.json",
        "environment": "staging",
    }
    kwargs[field_name] = repo_root / relative_target

    with pytest.raises(
        ValueError,
        match=rf"{field_name} must not overwrite migration source, template, or validator files",
    ):
        generate_managed_migration_env(**kwargs)
