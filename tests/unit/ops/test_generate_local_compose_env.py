from __future__ import annotations

import base64
from pathlib import Path
import subprocess

import pytest

import scripts.generate_local_compose_env as local_compose_env_generator
from scripts.generate_local_compose_env import generate_local_compose_env


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def test_generate_local_compose_env_is_deterministic(tmp_path: Path) -> None:
    template = tmp_path / ".env.example"
    output = tmp_path / ".env.compose.dev"
    _write(
        template,
        "\n".join(
            [
                "APP_NAME=Valdrics",
                "DEBUG=false",
                "POSTGRES_PASSWORD=",
                "GRAFANA_PASSWORD=",
                "CSRF_SECRET_KEY=",
                "ENCRYPTION_KEY=",
            ]
        ),
    )

    generate_local_compose_env(
        template_path=template, output_path=output, seed="seed-1"
    )
    first = output.read_text(encoding="utf-8")
    generate_local_compose_env(
        template_path=template, output_path=output, seed="seed-1"
    )
    second = output.read_text(encoding="utf-8")

    assert first == second


def test_generate_local_compose_env_derives_required_key_shapes(tmp_path: Path) -> None:
    template = tmp_path / ".env.example"
    output = tmp_path / ".env.compose.dev"
    _write(
        template,
        "\n".join(
            [
                "POSTGRES_PASSWORD=",
                "GRAFANA_PASSWORD=",
                "CSRF_SECRET_KEY=",
                "ENCRYPTION_KEY=",
                "SUPABASE_JWT_SECRET=",
                "KDF_SALT=",
                "ADMIN_API_KEY=",
                "INTERNAL_JOB_SECRET=",
                "INTERNAL_METRICS_AUTH_TOKEN=",
                "ENFORCEMENT_APPROVAL_TOKEN_SECRET=",
                "ENFORCEMENT_EXPORT_SIGNING_SECRET=",
            ]
        ),
    )

    generate_local_compose_env(
        template_path=template, output_path=output, seed="seed-2"
    )
    values = _parse_env(output)

    assert values["TESTING"] == "false"
    assert values["ENVIRONMENT"] == "development"
    assert values["API_URL"] == "http://localhost:8000"
    assert values["FRONTEND_URL"] == "http://localhost:3000"
    assert values["ORIGIN"] == "http://localhost:3000"
    assert values["REDIS_URL"] == "redis://redis:6379"
    assert values["POSTGRES_DB"] == "valdrics"
    assert values["POSTGRES_USER"] == "postgres"
    assert (
        values["AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN"]
        == "arn:aws:iam::000000000000:role/ValdricsLocalComposeControlPlane"
    )
    assert values["DATABASE_URL"].startswith("postgresql+asyncpg://postgres:")
    assert values["DATABASE_URL"].endswith("@postgres:5432/valdrics")
    assert len(values["POSTGRES_PASSWORD"]) == 48
    assert len(values["GRAFANA_PASSWORD"]) == 48
    assert len(values["CSRF_SECRET_KEY"]) >= 32
    assert len(values["SUPABASE_JWT_SECRET"]) >= 32
    assert len(values["ADMIN_API_KEY"]) >= 32
    assert len(values["INTERNAL_JOB_SECRET"]) >= 32
    assert len(values["INTERNAL_METRICS_AUTH_TOKEN"]) >= 32
    assert len(values["ENFORCEMENT_APPROVAL_TOKEN_SECRET"]) >= 32
    assert len(values["ENFORCEMENT_EXPORT_SIGNING_SECRET"]) >= 32
    assert len(values["ENCRYPTION_KEY"]) >= 32
    assert len(base64.b64decode(values["KDF_SALT"])) == 32


def test_generate_local_compose_env_changes_with_seed(tmp_path: Path) -> None:
    template = tmp_path / ".env.example"
    out_a = tmp_path / "a.env.compose.dev"
    out_b = tmp_path / "b.env.compose.dev"
    _write(template, "POSTGRES_PASSWORD=\nGRAFANA_PASSWORD=\nCSRF_SECRET_KEY=\n")

    generate_local_compose_env(template_path=template, output_path=out_a, seed="seed-A")
    generate_local_compose_env(template_path=template, output_path=out_b, seed="seed-B")
    values_a = _parse_env(out_a)
    values_b = _parse_env(out_b)

    assert values_a["POSTGRES_PASSWORD"] != values_b["POSTGRES_PASSWORD"]
    assert values_a["GRAFANA_PASSWORD"] != values_b["GRAFANA_PASSWORD"]
    assert values_a["CSRF_SECRET_KEY"] != values_b["CSRF_SECRET_KEY"]


def test_generate_local_compose_env_is_shell_source_safe_for_json_values(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.example"
    output = tmp_path / ".env.compose.dev"
    _write(
        template,
        "\n".join(
            [
                'CORS_ORIGINS=["http://localhost:3000","http://localhost:5174"]',
                "ORIGIN=",
                "POSTGRES_PASSWORD=",
                "GRAFANA_PASSWORD=",
                "CSRF_SECRET_KEY=",
            ]
        ),
    )

    generate_local_compose_env(
        template_path=template, output_path=output, seed="seed-3"
    )

    sourced = subprocess.run(
        ["bash", "-lc", f"set -a && source {output} && printf '%s' \"$CORS_ORIGINS\""],
        check=True,
        capture_output=True,
        text=True,
    )

    assert (
        sourced.stdout
        == '["http://localhost:3000","http://localhost:5174","http://localhost:5173"]'
    )

    sourced_origin = subprocess.run(
        ["bash", "-lc", f"set -a && source {output} && printf '%s' \"$ORIGIN\""],
        check=True,
        capture_output=True,
        text=True,
    )
    assert sourced_origin.stdout == "http://localhost:3000"


def test_generate_local_compose_env_creates_parent_directories(tmp_path: Path) -> None:
    template = tmp_path / ".env.example"
    output = tmp_path / "nested" / "local" / ".env.compose.dev"
    _write(template, "POSTGRES_PASSWORD=\nGRAFANA_PASSWORD=\n")

    result = generate_local_compose_env(
        template_path=template, output_path=output, seed="seed-4"
    )

    assert result == output
    assert output.exists()


def test_generate_local_compose_env_rejects_template_output_path_collision(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.compose.dev"
    _write(template, "POSTGRES_PASSWORD=\nGRAFANA_PASSWORD=\n")

    with pytest.raises(
        ValueError, match="template_path and output_path must be different files"
    ):
        generate_local_compose_env(
            template_path=template,
            output_path=template,
            seed="seed-5",
        )


@pytest.mark.parametrize(
    "relative_output",
    [
        ".env.example",
        ".env.dev",
        "scripts/generate_local_compose_env.py",
        "docs/ops/evidence/finance_guardrails_TEMPLATE.json",
        "docs/ops/evidence/README.md",
    ],
)
def test_generate_local_compose_env_rejects_protected_output_targets(
    tmp_path: Path,
    relative_output: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    template = tmp_path / ".env.template"
    _write(template, "POSTGRES_PASSWORD=\nGRAFANA_PASSWORD=\n")

    with pytest.raises(
        ValueError,
        match="output_path must not overwrite local-compose source or tracked template files",
    ):
        generate_local_compose_env(
            template_path=template,
            output_path=repo_root / relative_output,
            seed="seed-6",
        )


def test_generate_local_compose_env_does_not_leave_output_when_promotion_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = tmp_path / ".env.template"
    output = tmp_path / ".env.compose.dev"
    path_type = type(output)
    original_replace = path_type.replace
    _write(template, "POSTGRES_PASSWORD=\nGRAFANA_PASSWORD=\n")

    def _failing_replace(self: Path, target: Path) -> Path:
        if self.parent == output.parent and Path(target) == output:
            raise OSError("simulated promotion failure")
        return original_replace(self, target)

    monkeypatch.setattr(path_type, "replace", _failing_replace)

    with pytest.raises(OSError, match="simulated promotion failure"):
        generate_local_compose_env(
            template_path=template,
            output_path=output,
            seed="seed-7",
        )

    assert not output.exists()
    assert not list(output.parent.glob(f".{output.stem}.*{output.suffix}.tmp"))


def test_main_resolves_default_paths_from_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def _fake_generate_local_compose_env(**kwargs: object) -> Path:
        captured.update(kwargs)
        return kwargs["output_path"]  # type: ignore[return-value]

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        local_compose_env_generator,
        "generate_local_compose_env",
        _fake_generate_local_compose_env,
    )

    assert local_compose_env_generator.main([]) == 0
    assert (
        captured["template_path"]
        == (
            local_compose_env_generator._repo_root()
            / local_compose_env_generator.DEFAULT_TEMPLATE_PATH
        ).resolve()
    )
    assert (
        captured["output_path"]
        == (
            local_compose_env_generator._repo_root()
            / local_compose_env_generator.DEFAULT_OUTPUT_PATH
        ).resolve()
    )


def test_main_rejects_relative_paths_that_escape_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)

    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(local_compose_env_generator, "_repo_root", lambda: repo_root)

    with pytest.raises(
        ValueError, match="template_path must stay within repo root when relative"
    ):
        local_compose_env_generator.main(
            [
                "--template-path",
                "../escape/.env.example",
                "--output-path",
                ".env.compose.dev",
            ]
        )
