from __future__ import annotations

from typing import Any

AWS_CREDENTIAL_MAPPING = {
    "AccessKeyId": "aws_access_key_id",
    "SecretAccessKey": "aws_secret_access_key",  # nosec B105 - AWS field name
    "SessionToken": "aws_session_token",  # nosec B105 - AWS field name
    "aws_access_key_id": "aws_access_key_id",
    "aws_secret_access_key": "aws_secret_access_key",  # nosec B105 - AWS field name
    "aws_session_token": "aws_session_token",  # nosec B105 - AWS field name
}


def map_aws_credentials(credentials: dict[str, Any] | None) -> dict[str, str]:
    """Map AWS-style credential payloads to boto-compatible keyword arguments."""
    mapped: dict[str, str] = {}
    if not credentials:
        return mapped

    for src, dst in AWS_CREDENTIAL_MAPPING.items():
        value = credentials.get(src)
        if value is not None:
            mapped[dst] = str(value)

    return mapped
