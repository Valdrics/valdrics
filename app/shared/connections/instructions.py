from app.shared.connections.instructions_catalog import (
    get_license_connector_catalog,
    get_saas_connector_catalog,
)
from app.shared.connections.instructions_snippets import (
    build_azure_setup_snippet,
    build_gcp_setup_snippet,
    build_hybrid_setup_snippet,
    build_license_setup_snippet,
    build_platform_setup_snippet,
    build_saas_setup_snippet,
)
from app.shared.core.config import get_settings


class ConnectionInstructionService:
    """
    Generates setup instructions and CLI snippets for cloud connections.
    Encapsulates string building logic to keep API routes clean.
    """

    @staticmethod
    def get_azure_setup_snippet(tenant_id: str) -> dict[str, str]:
        settings = get_settings()
        issuer = settings.API_URL.rstrip("/")
        return build_azure_setup_snippet(tenant_id, issuer)

    @staticmethod
    def get_gcp_setup_snippet(tenant_id: str) -> dict[str, str]:
        settings = get_settings()
        issuer = settings.API_URL.rstrip("/")
        return build_gcp_setup_snippet(tenant_id, issuer)

    @staticmethod
    def get_saas_setup_snippet(tenant_id: str) -> dict[str, object]:
        settings = get_settings()
        api_url = settings.API_URL.rstrip("/")
        return build_saas_setup_snippet(
            tenant_id,
            api_url,
            ConnectionInstructionService.get_saas_connector_catalog(),
        )

    @staticmethod
    def get_license_setup_snippet(tenant_id: str) -> dict[str, object]:
        settings = get_settings()
        api_url = settings.API_URL.rstrip("/")
        return build_license_setup_snippet(
            tenant_id,
            api_url,
            ConnectionInstructionService.get_license_connector_catalog(),
        )

    @staticmethod
    def get_platform_setup_snippet(tenant_id: str) -> dict[str, object]:
        settings = get_settings()
        api_url = settings.API_URL.rstrip("/")
        return build_platform_setup_snippet(tenant_id, api_url)

    @staticmethod
    def get_hybrid_setup_snippet(tenant_id: str) -> dict[str, object]:
        settings = get_settings()
        api_url = settings.API_URL.rstrip("/")
        return build_hybrid_setup_snippet(tenant_id, api_url)

    @staticmethod
    def get_saas_connector_catalog() -> list[dict[str, object]]:
        return get_saas_connector_catalog()

    @staticmethod
    def get_license_connector_catalog() -> list[dict[str, object]]:
        return get_license_connector_catalog()
