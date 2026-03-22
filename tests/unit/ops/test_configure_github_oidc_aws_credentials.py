from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import scripts.configure_github_oidc_aws_credentials as oidc_script


def test_build_oidc_request_url_appends_audience() -> None:
    url = oidc_script._build_oidc_request_url(
        base_url="https://token.actions.githubusercontent.com",
        audience="sts.amazonaws.com",
    )

    assert url.endswith("?audience=sts.amazonaws.com")


def test_main_writes_short_lived_aws_credentials(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out_path = tmp_path / "aws-oidc-evidence.json"
    github_env_path = tmp_path / "github.env"

    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_URL", "https://token.example.com")
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "request-token")
    monkeypatch.setenv("GITHUB_ENV", str(github_env_path))
    monkeypatch.setattr(
        oidc_script,
        "_parse_args",
        lambda _argv=None: SimpleNamespace(
            role_arn="arn:aws:iam::123456789012:role/github-actions-failover",
            region="us-west-2",
            session_name="regional-failover-123",
            audience="sts.amazonaws.com",
            out=str(out_path),
        ),
    )
    monkeypatch.setattr(
        oidc_script,
        "_fetch_github_oidc_token",
        lambda **kwargs: "github-oidc-token",
    )
    monkeypatch.setattr(
        oidc_script,
        "_assume_role_with_web_identity",
        lambda **kwargs: (
            {
                "AccessKeyId": "ASIAEXAMPLE",
                "SecretAccessKey": "secret-value",
                "SessionToken": "session-value",
            },
            {
                "Account": "123456789012",
                "Arn": "arn:aws:sts::123456789012:assumed-role/github-actions-failover/regional-failover-123",
                "UserId": "AROAXYZ:regional-failover-123",
            },
        ),
    )

    assert oidc_script.main() == 0

    env_lines = github_env_path.read_text(encoding="utf-8").splitlines()
    assert "AWS_ACCESS_KEY_ID=ASIAEXAMPLE" in env_lines
    assert "AWS_SECRET_ACCESS_KEY=secret-value" in env_lines
    assert "AWS_SESSION_TOKEN=session-value" in env_lines
    assert "AWS_DEFAULT_REGION=us-west-2" in env_lines
    assert "AWS_REGION=us-west-2" in env_lines
    assert (
        "FAILOVER_AWS_ROLE_TO_ASSUME="
        "arn:aws:iam::123456789012:role/github-actions-failover"
    ) in env_lines

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["assumed_identity"]["account"] == "123456789012"
    assert payload["role_arn"].endswith(":role/github-actions-failover")

    stdout_payload = json.loads(capsys.readouterr().out)
    assert stdout_payload["session_name"] == "regional-failover-123"


def test_main_resolves_relative_out_from_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    github_env_path = tmp_path / "github.env"
    resolved_out = tmp_path / "artifacts" / "aws-oidc-evidence.json"

    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_URL", "https://token.example.com")
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "request-token")
    monkeypatch.setenv("GITHUB_ENV", str(github_env_path))
    monkeypatch.setattr(oidc_script, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        oidc_script,
        "_parse_args",
        lambda _argv=None: SimpleNamespace(
            role_arn="arn:aws:iam::123456789012:role/github-actions-failover",
            region="us-west-2",
            session_name="regional-failover-123",
            audience="sts.amazonaws.com",
            out="artifacts/aws-oidc-evidence.json",
        ),
    )
    monkeypatch.setattr(
        oidc_script,
        "_fetch_github_oidc_token",
        lambda **kwargs: "github-oidc-token",
    )
    monkeypatch.setattr(
        oidc_script,
        "_assume_role_with_web_identity",
        lambda **kwargs: (
            {
                "AccessKeyId": "ASIAEXAMPLE",
                "SecretAccessKey": "secret-value",
                "SessionToken": "session-value",
            },
            {
                "Account": "123456789012",
                "Arn": "arn:aws:sts::123456789012:assumed-role/github-actions-failover/regional-failover-123",
                "UserId": "AROAXYZ:regional-failover-123",
            },
        ),
    )

    assert oidc_script.main() == 0
    assert json.loads(resolved_out.read_text(encoding="utf-8"))["role_arn"].endswith(
        ":role/github-actions-failover"
    )


def test_main_rejects_directory_out_path_before_exchange(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir = tmp_path / "artifacts"
    output_dir.mkdir()
    github_env_path = tmp_path / "github.env"
    github_env_path.write_text("", encoding="utf-8")

    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_URL", "https://token.example.com")
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "request-token")
    monkeypatch.setenv("GITHUB_ENV", str(github_env_path))
    monkeypatch.setattr(
        oidc_script,
        "_parse_args",
        lambda _argv=None: SimpleNamespace(
            role_arn="arn:aws:iam::123456789012:role/github-actions-failover",
            region="us-west-2",
            session_name="regional-failover-123",
            audience="sts.amazonaws.com",
            out=str(output_dir),
        ),
    )
    monkeypatch.setattr(
        oidc_script,
        "_fetch_github_oidc_token",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not fetch token")),
    )

    assert oidc_script.main() == 2
    assert "out must be a file path" in capsys.readouterr().out
