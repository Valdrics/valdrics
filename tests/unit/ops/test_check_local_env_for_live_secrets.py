from __future__ import annotations

from pathlib import Path

from scripts.security.check_local_env_for_live_secrets import is_live_secret_value, main


def _write_env(tmp_path: Path, content: str) -> None:
    (tmp_path / ".env").write_text(content, encoding="utf-8")


def test_main_flags_live_paystack_keys(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "scripts.security.check_local_env_for_live_secrets._repo_root",
        lambda: tmp_path,
    )
    _write_env(
        tmp_path,
        "PAYSTACK_SECRET_KEY=sk_live_1234567890\nPAYSTACK_PUBLIC_KEY=pk_live_1234567890\n",
    )

    assert main([]) == 1
    output = capsys.readouterr().out
    assert "PAYSTACK_SECRET_KEY" in output
    assert "PAYSTACK_PUBLIC_KEY" in output


def test_main_ignores_explicit_synthetic_validation_keys(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "scripts.security.check_local_env_for_live_secrets._repo_root",
        lambda: tmp_path,
    )
    _write_env(
        tmp_path,
        (
            "PAYSTACK_SECRET_KEY=example_paystack_secret_ci_validation_only\n"
            "PAYSTACK_PUBLIC_KEY=example_paystack_public_ci_validation_only\n"
        ),
    )

    assert main([]) == 0
    assert "No known live-secret patterns detected" in capsys.readouterr().out


def test_main_flags_modern_openai_and_temporary_aws_keys(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "scripts.security.check_local_env_for_live_secrets._repo_root",
        lambda: tmp_path,
    )
    _write_env(
        tmp_path,
        (
            "OPENAI_API_KEY=sk-proj-abc123XYZ\n"
            "AWS_ACCESS_KEY_ID=ASIA1234567890ABCDEF\n"
        ),
    )

    assert main([]) == 1
    output = capsys.readouterr().out
    assert "OPENAI_API_KEY" in output
    assert "AWS_ACCESS_KEY_ID" in output


def test_is_live_secret_value_covers_modern_secret_formats() -> None:
    assert is_live_secret_value("OPENAI_API_KEY", "sk-proj-abc123XYZ")
    assert is_live_secret_value("AWS_ACCESS_KEY_ID", "ASIA1234567890ABCDEF")
    assert not is_live_secret_value("OPENAI_API_KEY", "example_openai_key")


def test_main_resolves_relative_env_file_from_repo_root(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    env_file = repo_root / "custom.env"
    env_file.write_text("OPENAI_API_KEY=sk-proj-abc123XYZ\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "scripts.security.check_local_env_for_live_secrets._repo_root",
        lambda: repo_root,
    )

    assert main(["--env-file", "custom.env"]) == 1
    assert "OPENAI_API_KEY" in capsys.readouterr().out


def test_main_rejects_directory_env_file(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    repo_root = tmp_path / "repo"
    env_dir = repo_root / "envdir"
    env_dir.mkdir(parents=True)
    monkeypatch.setattr(
        "scripts.security.check_local_env_for_live_secrets._repo_root",
        lambda: repo_root,
    )

    assert main(["--env-file", "envdir"]) == 2
    assert "--env-file must be a file path" in capsys.readouterr().out
