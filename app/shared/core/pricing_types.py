from __future__ import annotations

from enum import Enum


class PricingTier(str, Enum):
    """Available subscription tiers."""

    FREE = "free"
    STARTER = "starter"
    GROWTH = "growth"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class FeatureFlag(str, Enum):
    """Feature flags for tier gating."""

    DASHBOARDS = "dashboards"
    COST_TRACKING = "cost_tracking"
    ALERTS = "alerts"
    SLACK_INTEGRATION = "slack_integration"
    JIRA_INTEGRATION = "jira_integration"
    ZOMBIE_SCAN = "zombie_scan"
    LLM_ANALYSIS = "llm_analysis"
    AI_INSIGHTS = "ai_insights"
    MULTI_CLOUD = "multi_cloud"
    MULTI_REGION = "multi_region"
    GREENOPS = "greenops"
    CARBON_TRACKING = "carbon_tracking"
    AUTO_REMEDIATION = "auto_remediation"
    API_ACCESS = "api_access"
    FORECASTING = "forecasting"
    SSO = "sso"
    SCIM = "scim"
    DEDICATED_SUPPORT = "dedicated_support"
    AUDIT_LOGS = "audit_logs"
    HOURLY_SCANS = "hourly_scans"
    AI_ANALYSIS_DETAILED = "ai_analysis_detailed"
    DOMAIN_DISCOVERY = "domain_discovery"
    IDP_DEEP_SCAN = "idp_deep_scan"
    PRECISION_DISCOVERY = "precision_discovery"
    OWNER_ATTRIBUTION = "owner_attribution"
    GITOPS_REMEDIATION = "gitops_remediation"
    UNIT_ECONOMICS = "unit_economics"
    INGESTION_SLA = "ingestion_sla"
    INGESTION_BACKFILL = "ingestion_backfill"
    ANOMALY_DETECTION = "anomaly_detection"
    CHARGEBACK = "chargeback"
    RECONCILIATION = "reconciliation"
    CLOSE_WORKFLOW = "close_workflow"
    CARBON_ASSURANCE = "carbon_assurance"
    CLOUD_PLUS_CONNECTORS = "cloud_plus_connectors"
    COMPLIANCE_EXPORTS = "compliance_exports"
    SAVINGS_PROOF = "savings_proof"
    COMMITMENT_OPTIMIZATION = "commitment_optimization"
    POLICY_PREVIEW = "policy_preview"
    POLICY_CONFIGURATION = "policy_configuration"
    ESCALATION_WORKFLOW = "escalation_workflow"
    INCIDENT_INTEGRATIONS = "incident_integrations"


class FeatureMaturity(str, Enum):
    """Feature maturity metadata for packaging transparency."""

    GA = "GA"
    BETA = "Beta"
    PREVIEW = "Preview"


__all__ = [
    "PricingTier",
    "FeatureFlag",
    "FeatureMaturity",
]
