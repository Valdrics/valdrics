import sys
from importlib import import_module
from importlib.util import find_spec
from unittest.mock import MagicMock
import pytest

# Global mock for Azure SDKs to prevent ImportErrors in CI/Test
mock_modules = [
    "azure.mgmt.cognitiveservices",
    "azure.mgmt.search",
    "azure.mgmt.monitor",
    "azure.mgmt.compute",
    "azure.mgmt.compute.aio",
    "azure.mgmt.storage",
    "azure.mgmt.network",
    "azure.mgmt.costmanagement",
    "azure.mgmt.costmanagement.aio",
    "azure.core",
    "azure.core.credentials",
    "azure.core.exceptions",
    "azure.core.pipeline",
    "azure.core.pipeline.transport",
    "azure.core.pipeline.policies",
    "azure.core.rest",
]


def _module_available(module_name: str) -> bool:
    try:
        return find_spec(module_name) is not None
    except (ModuleNotFoundError, ValueError):
        return False


for mod in mock_modules:
    if mod not in sys.modules:
        if _module_available(mod):
            continue
        sys.modules[mod] = MagicMock()


@pytest.fixture
def mock_azure_creds() -> dict[str, str]:
    return {
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "client_id": "00000000-0000-0000-0000-000000000002",
        "client_secret": "secret-123",
        "subscription_id": "00000000-0000-0000-0000-000000000003",
    }


@pytest.fixture(autouse=True)
def stub_azure_identity_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_credential = MagicMock(name="azure_identity_credential")
    module_names = [
        "app.modules.optimization.adapters.azure.detector",
        "app.modules.optimization.adapters.azure.plugins.ai",
        "app.modules.optimization.adapters.azure.plugins.compute",
        "app.modules.optimization.adapters.azure.plugins.containers",
        "app.modules.optimization.adapters.azure.plugins.network",
        "app.modules.optimization.adapters.azure.plugins.storage",
    ]

    for module_name in module_names:
        module = import_module(module_name)
        if hasattr(module, "ClientSecretCredential"):
            monkeypatch.setattr(
                module,
                "ClientSecretCredential",
                lambda *args, **kwargs: dummy_credential,
            )
        if hasattr(module, "DefaultAzureCredential"):
            monkeypatch.setattr(
                module,
                "DefaultAzureCredential",
                lambda *args, **kwargs: dummy_credential,
            )
