from __future__ import annotations


def get_saas_connector_catalog() -> list[dict[str, object]]:
    return [
        {
            "vendor": "stripe",
            "display_name": "Stripe",
            "recommended_auth_method": "api_key",
            "supported_auth_methods": ["api_key", "manual", "csv"],
            "required_connector_config_fields": [],
        },
        {
            "vendor": "salesforce",
            "display_name": "Salesforce",
            "recommended_auth_method": "oauth",
            "supported_auth_methods": ["oauth", "api_key", "manual", "csv"],
            "required_connector_config_fields": ["instance_url"],
        },
    ]


def get_license_connector_catalog() -> list[dict[str, object]]:
    return [
        {
            "vendor": "microsoft_365",
            "display_name": "Microsoft 365",
            "recommended_auth_method": "oauth",
            "supported_auth_methods": ["oauth", "api_key", "manual", "csv"],
            "required_connector_config_fields": [],
            "optional_connector_config_fields": [
                "default_seat_price_usd",
                "sku_prices",
                "currency",
            ],
        },
        {
            "vendor": "google_workspace",
            "display_name": "Google Workspace",
            "recommended_auth_method": "oauth",
            "supported_auth_methods": ["oauth", "api_key", "manual", "csv"],
            "required_connector_config_fields": [],
            "optional_connector_config_fields": [
                "default_seat_price_usd",
                "sku_prices",
                "currency",
            ],
        },
        {
            "vendor": "github",
            "display_name": "GitHub (License Governance)",
            "recommended_auth_method": "api_key",
            "supported_auth_methods": ["api_key", "oauth", "manual", "csv"],
            "required_connector_config_fields": [],
            "optional_connector_config_fields": ["github_org"],
        },
        {
            "vendor": "slack",
            "display_name": "Slack (License Governance)",
            "recommended_auth_method": "api_key",
            "supported_auth_methods": ["api_key", "oauth", "manual", "csv"],
            "required_connector_config_fields": [],
            "optional_connector_config_fields": ["slack_team_id"],
        },
        {
            "vendor": "zoom",
            "display_name": "Zoom (License Governance)",
            "recommended_auth_method": "api_key",
            "supported_auth_methods": ["api_key", "oauth", "manual", "csv"],
            "required_connector_config_fields": [],
            "optional_connector_config_fields": [],
        },
        {
            "vendor": "salesforce",
            "display_name": "Salesforce (License Governance)",
            "recommended_auth_method": "oauth",
            "supported_auth_methods": ["oauth", "api_key", "manual", "csv"],
            "required_connector_config_fields": ["salesforce_instance_url"],
            "optional_connector_config_fields": ["salesforce_api_version"],
        },
    ]
