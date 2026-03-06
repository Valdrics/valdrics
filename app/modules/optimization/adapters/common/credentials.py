"""Credential resolution helpers for optimization adapters."""

from __future__ import annotations

from typing import Any


def resolve_azure_credentials(raw_credentials: Any) -> Any:
    """Resolve Azure credentials from either structured secrets or credential objects."""
    if raw_credentials is not None and not isinstance(raw_credentials, dict):
        get_token = getattr(raw_credentials, "get_token", None)
        if callable(get_token):
            return raw_credentials
        raise ValueError("Unsupported Azure credential format")

    try:
        from azure.identity import ClientSecretCredential, DefaultAzureCredential
    except ImportError as exc:  # pragma: no cover - exercised only when SDK is absent
        raise ValueError("Azure identity SDK is unavailable") from exc

    if raw_credentials is None:
        return DefaultAzureCredential()

    if isinstance(raw_credentials, dict):
        tenant_id = str(raw_credentials.get("tenant_id") or "").strip()
        client_id = str(raw_credentials.get("client_id") or "").strip()
        client_secret = str(raw_credentials.get("client_secret") or "").strip()
        missing = [
            key
            for key, value in (
                ("tenant_id", tenant_id),
                ("client_id", client_id),
                ("client_secret", client_secret),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                "Azure credentials dict missing required fields: "
                + ", ".join(sorted(missing))
            )
        return ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

    if isinstance(raw_credentials, (ClientSecretCredential, DefaultAzureCredential)):
        return raw_credentials

    raise ValueError("Unsupported Azure credential format")


def resolve_gcp_credentials(raw_credentials: Any) -> Any:
    """Resolve GCP credentials from service account payloads or credential objects."""
    if raw_credentials is not None and not isinstance(raw_credentials, dict):
        before_request = getattr(raw_credentials, "before_request", None)
        if callable(before_request):
            return raw_credentials
        raise ValueError("Unsupported GCP credential format")

    try:
        from google.auth.credentials import Credentials as GoogleCredentials
        from google.oauth2 import service_account
    except ImportError as exc:  # pragma: no cover - exercised only when SDK is absent
        raise ValueError("GCP auth SDK is unavailable") from exc

    if raw_credentials is None:
        return None

    if isinstance(raw_credentials, dict):
        required = ("client_email", "private_key", "token_uri")
        missing = [key for key in required if not str(raw_credentials.get(key) or "").strip()]
        if missing:
            raise ValueError(
                "GCP service-account credentials missing required fields: "
                + ", ".join(sorted(missing))
            )
        return service_account.Credentials.from_service_account_info(raw_credentials)  # type: ignore[no-untyped-call]

    if isinstance(raw_credentials, GoogleCredentials):
        return raw_credentials

    raise ValueError("Unsupported GCP credential format")
