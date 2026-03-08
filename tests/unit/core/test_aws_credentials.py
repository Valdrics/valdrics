from __future__ import annotations

from app.shared.core.aws_credentials import map_aws_credentials


def test_map_aws_credentials_supports_camel_and_snake_case() -> None:
    assert map_aws_credentials(
        {
            "AccessKeyId": "AKIA",
            "SecretAccessKey": "secret",
            "SessionToken": "token",
        }
    ) == {
        "aws_access_key_id": "AKIA",
        "aws_secret_access_key": "secret",
        "aws_session_token": "token",
    }


def test_map_aws_credentials_ignores_missing_values() -> None:
    assert map_aws_credentials({"aws_access_key_id": "AKIA"}) == {
        "aws_access_key_id": "AKIA"
    }
    assert map_aws_credentials(None) == {}
