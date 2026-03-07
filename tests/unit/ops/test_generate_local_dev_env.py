from __future__ import annotations

import base64
from pathlib import Path

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
                "INTERNAL_JOB_SECRET=",
                "ENFORCEMENT_EXPORT_SIGNING_SECRET=",
            ]
        ),
    )

    generate_local_dev_env(template_path=template, output_path=output, seed="seed-2")
    values = _parse_env(output)

    assert values["TESTING"] == "true"
    assert values["ENVIRONMENT"] == "development"
    assert len(values["CSRF_SECRET_KEY"]) >= 32
    assert len(values["SUPABASE_JWT_SECRET"]) >= 32
    assert len(values["ADMIN_API_KEY"]) >= 32
    assert len(values["INTERNAL_JOB_SECRET"]) >= 32
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
