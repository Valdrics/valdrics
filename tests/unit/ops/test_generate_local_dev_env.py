from __future__ import annotations

import base64
from pathlib import Path
import subprocess

import pytest

import scripts.generate_local_dev_env as local_dev_env_generator
from scripts.generate_local_dev_env import generate_local_dev_env


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


def test_generate_local_dev_env_is_deterministic(tmp_path: Path) -> None:
    template = tmp_path / ".env.example"
    output = tmp_path / ".env.dev"
    _write(
        template,
        "\n".join(
            [
                "APP_NAME=Valdrics",
                "DEBUG=false",
                "ENVIRONMENT=development",
                "CSRF_SECRET_KEY=",
                "ENCRYPTION_KEY=",
                "SUPABASE_JWT_SECRET=",
                "KDF_SALT=",
                "ADMIN_API_KEY=",
                "DATABASE_URL=postgresql+asyncpg://user:pass@host/db",
            ]
        ),
    )

    generate_local_dev_env(template_path=template, output_path=output, seed="seed-1")
    first = output.read_text(encoding="utf-8")
    generate_local_dev_env(template_path=template, output_path=output, seed="seed-1")
    second = output.read_text(encoding="utf-8")

    assert first == second


def test_generate_local_dev_env_derives_required_key_shapes(tmp_path: Path) -> None:
    template = tmp_path / ".env.example"
    output = tmp_path / ".env.dev"
    _write(
        template,
        "\n".join(
            [
                "CSRF_SECRET_KEY=",
                "ENCRYPTION_KEY=",
                "SUPABASE_JWT_SECRET=",
                "KDF_SALT=",
                "ADMIN_API_KEY=",
                "ENFORCEMENT_APPROVAL_TOKEN_SECRET=",
                "ENFORCEMENT_EXPORT_SIGNING_SECRET=",
            ]
        ),
    )

    generate_local_dev_env(template_path=template, output_path=output, seed="seed-2")
    values = _parse_env(output)

    assert values["TESTING"] == "false"
    assert values["ENVIRONMENT"] == "local"
    assert values["LOCAL_SQLITE_BOOTSTRAP"] == "true"
    assert values["DB_SSL_MODE"] == "disable"
    assert "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN" not in values
    assert len(values["CSRF_SECRET_KEY"]) >= 32
    assert len(values["SUPABASE_JWT_SECRET"]) >= 32
    assert len(values["ADMIN_API_KEY"]) >= 32
    assert len(values["ENFORCEMENT_APPROVAL_TOKEN_SECRET"]) >= 32
    assert len(values["ENFORCEMENT_EXPORT_SIGNING_SECRET"]) >= 32
    assert len(values["ENCRYPTION_KEY"]) >= 32
    assert len(base64.b64decode(values["KDF_SALT"])) == 32


def test_generate_local_dev_env_changes_with_seed(tmp_path: Path) -> None:
    template = tmp_path / ".env.example"
    out_a = tmp_path / "a.env.dev"
    out_b = tmp_path / "b.env.dev"
    _write(template, "CSRF_SECRET_KEY=\nENCRYPTION_KEY=\n")

    generate_local_dev_env(template_path=template, output_path=out_a, seed="seed-A")
    generate_local_dev_env(template_path=template, output_path=out_b, seed="seed-B")
    values_a = _parse_env(out_a)
    values_b = _parse_env(out_b)

    assert values_a["CSRF_SECRET_KEY"] != values_b["CSRF_SECRET_KEY"]
    assert values_a["ENCRYPTION_KEY"] != values_b["ENCRYPTION_KEY"]


def test_generate_local_dev_env_is_shell_source_safe_for_json_values(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.example"
    output = tmp_path / ".env.dev"
    _write(
        template,
        "\n".join(
            [
                'CORS_ORIGINS=["http://localhost:5173","http://localhost:5174"]',
                "CSRF_SECRET_KEY=",
                "ENCRYPTION_KEY=",
                "SUPABASE_JWT_SECRET=",
                "KDF_SALT=",
            ]
        ),
    )

    generate_local_dev_env(template_path=template, output_path=output, seed="seed-3")

    sourced = subprocess.run(
        ["bash", "-lc", f"set -a && source {output} && printf '%s' \"$CORS_ORIGINS\""],
        check=True,
        capture_output=True,
        text=True,
    )

    assert sourced.stdout == '["http://localhost:5173","http://localhost:5174"]'


def test_generate_local_dev_env_creates_parent_directories(tmp_path: Path) -> None:
    template = tmp_path / ".env.example"
    output = tmp_path / "nested" / "local" / ".env.dev"
    _write(template, "CSRF_SECRET_KEY=\nENCRYPTION_KEY=\n")

    result = generate_local_dev_env(
        template_path=template, output_path=output, seed="seed-4"
    )

    assert result == output
    assert output.exists()


def test_generate_local_dev_env_rejects_template_output_path_collision(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.dev"
    _write(template, "CSRF_SECRET_KEY=\nENCRYPTION_KEY=\n")

    import pytest

    with pytest.raises(
        ValueError, match="template_path and output_path must be different files"
    ):
        generate_local_dev_env(
            template_path=template, output_path=template, seed="seed-5"
        )


def test_generate_local_dev_env_rejects_non_file_template_path(
    tmp_path: Path,
) -> None:
    template_dir = tmp_path / "template-dir"
    template_dir.mkdir()
    output = tmp_path / ".env.dev"

    import pytest

    with pytest.raises(ValueError, match="template_path must be a file"):
        generate_local_dev_env(
            template_path=template_dir, output_path=output, seed="seed-6"
        )


def test_generate_local_dev_env_rejects_directory_output_path(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.example"
    output_dir = tmp_path / "output-dir"
    output_dir.mkdir()
    _write(template, "CSRF_SECRET_KEY=\nENCRYPTION_KEY=\n")

    import pytest

    with pytest.raises(ValueError, match="output_path must be a file path"):
        generate_local_dev_env(
            template_path=template, output_path=output_dir, seed="seed-7"
        )


@pytest.mark.parametrize(
    "relative_output",
    [
        ".env.example",
        "scripts/generate_local_dev_env.py",
        "docs/ops/evidence/finance_guardrails_TEMPLATE.json",
        "docs/ops/key-rotation-drill-2026-02-27.md",
        "docs/ops/evidence/README.md",
    ],
)
def test_generate_local_dev_env_rejects_protected_output_targets(
    tmp_path: Path,
    relative_output: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    template = tmp_path / ".env.template"
    _write(template, "CSRF_SECRET_KEY=\nENCRYPTION_KEY=\n")

    import pytest

    with pytest.raises(
        ValueError,
        match="output_path must not overwrite local-dev source or tracked template files",
    ):
        generate_local_dev_env(
            template_path=template,
            output_path=repo_root / relative_output,
            seed="seed-8",
        )


def test_generate_local_dev_env_rejects_blocked_output_parent(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.template"
    blocked_parent = tmp_path / "blocked-parent"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")
    _write(template, "CSRF_SECRET_KEY=\nENCRYPTION_KEY=\n")

    with pytest.raises(ValueError, match="output_path parent must be a directory path"):
        generate_local_dev_env(
            template_path=template,
            output_path=blocked_parent / ".env.dev",
            seed="seed-9",
        )


def test_generate_local_dev_env_does_not_leave_output_when_promotion_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = tmp_path / ".env.template"
    output = tmp_path / ".env.dev"
    path_type = type(output)
    original_replace = path_type.replace
    _write(template, "CSRF_SECRET_KEY=\nENCRYPTION_KEY=\n")

    def _failing_replace(self: Path, target: Path) -> Path:
        if self.parent == output.parent and Path(target) == output:
            raise OSError("simulated promotion failure")
        return original_replace(self, target)

    monkeypatch.setattr(path_type, "replace", _failing_replace)

    with pytest.raises(OSError, match="simulated promotion failure"):
        generate_local_dev_env(
            template_path=template,
            output_path=output,
            seed="seed-10",
        )

    assert not output.exists()
    assert not list(output.parent.glob(f".{output.stem}.*{output.suffix}.tmp"))


def test_main_resolves_default_paths_from_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def _fake_generate_local_dev_env(**kwargs: object) -> Path:
        captured.update(kwargs)
        return kwargs["output_path"]  # type: ignore[return-value]

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        local_dev_env_generator,
        "generate_local_dev_env",
        _fake_generate_local_dev_env,
    )

    assert local_dev_env_generator.main([]) == 0
    assert (
        captured["template_path"]
        == (
            local_dev_env_generator._repo_root()
            / local_dev_env_generator.DEFAULT_TEMPLATE_PATH
        ).resolve()
    )
    assert (
        captured["output_path"]
        == (
            local_dev_env_generator._repo_root()
            / local_dev_env_generator.DEFAULT_OUTPUT_PATH
        ).resolve()
    )


def test_main_resolves_explicit_relative_paths_from_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    captured: dict[str, object] = {}

    def _fake_generate_local_dev_env(**kwargs: object) -> Path:
        captured.update(kwargs)
        return kwargs["output_path"]  # type: ignore[return-value]

    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(local_dev_env_generator, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(
        local_dev_env_generator,
        "generate_local_dev_env",
        _fake_generate_local_dev_env,
    )

    assert (
        local_dev_env_generator.main(
            [
                "--template-path",
                ".env.example",
                "--output-path",
                ".env.dev",
            ]
        )
        == 0
    )
    assert captured["template_path"] == (repo_root / ".env.example").resolve()
    assert captured["output_path"] == (repo_root / ".env.dev").resolve()


def test_main_rejects_relative_paths_that_escape_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)

    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(local_dev_env_generator, "_repo_root", lambda: repo_root)

    with pytest.raises(
        ValueError, match="template_path must stay within repo root when relative"
    ):
        local_dev_env_generator.main(
            [
                "--template-path",
                "../escape/.env.example",
                "--output-path",
                ".env.dev",
            ]
        )
