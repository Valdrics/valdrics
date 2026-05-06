from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from scripts import preflight_gcp_managed_platform


def test_validate_project_permissions_accepts_required_grants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout='{"permissions":["iam.serviceAccounts.create"]}',
            stderr="",
        )

    monkeypatch.setattr(preflight_gcp_managed_platform.subprocess, "run", fake_run)

    result = preflight_gcp_managed_platform.validate_project_permissions(
        project_id="valdrics-staging-001",
        required_permissions=("iam.serviceAccounts.create",),
    )

    assert result == {
        "granted_permissions": ["iam.serviceAccounts.create"],
        "required_permissions": ["iam.serviceAccounts.create"],
    }
    assert captured["command"] == [
        "gcloud",
        "projects",
        "test-iam-permissions",
        "valdrics-staging-001",
        "--permissions=iam.serviceAccounts.create",
        "--format=json",
    ]
    assert captured["kwargs"]["capture_output"] is True
    assert captured["kwargs"]["text"] is True


def test_validate_project_permissions_rejects_missing_grants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        preflight_gcp_managed_platform.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout='{"permissions":[]}',
            stderr="",
        ),
    )

    with pytest.raises(RuntimeError, match="iam.serviceAccounts.create"):
        preflight_gcp_managed_platform.validate_project_permissions(
            project_id="valdrics-staging-001",
            required_permissions=("iam.serviceAccounts.create",),
        )


def test_default_required_permissions_include_service_account_and_project_iam() -> None:
    assert "iam.serviceAccounts.create" in (
        preflight_gcp_managed_platform.DEFAULT_REQUIRED_PERMISSIONS
    )
    assert "resourcemanager.projects.setIamPolicy" in (
        preflight_gcp_managed_platform.DEFAULT_REQUIRED_PERMISSIONS
    )
