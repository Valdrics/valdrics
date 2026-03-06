"""Constants for PKG/FIN policy decision evidence validation."""

from __future__ import annotations

import re

ALLOWED_ENTERPRISE_PRICING_MODELS = {
    "flat_floor",
    "spend_based",
    "hybrid",
}
ALLOWED_GROWTH_AUTO_REMEDIATION_SCOPES = {
    "nonprod_only",
    "all_environments",
}
ALLOWED_PRO_ENFORCEMENT_BOUNDARY = {
    "required_for_prod_enforcement",
    "not_required",
}
ALLOWED_MIGRATION_STRATEGIES = {
    "grandfather_timeboxed",
    "contract_renewal_cutover",
    "immediate_cutover",
}
REQUIRED_TIERS = {"starter", "growth", "pro", "enterprise"}
ALLOWED_TELEMETRY_SOURCE_TYPES = {
    "synthetic_prelaunch",
    "production_observed",
}
ALLOWED_APPROVAL_GOVERNANCE_MODES = {
    "founder_acting_roles_prelaunch",
    "segregated_owners",
}
ALLOWED_DECISION_OWNER_FUNCTIONS = {
    "product",
    "finance",
    "go_to_market",
    "legal",
    "engineering",
    "operations",
}
ALLOWED_DECISION_RESOLUTIONS = {
    "locked_prelaunch",
    "scheduled_postlaunch",
}
REQUIRED_DECISION_BACKLOG_IDS: tuple[str, ...] = (
    "PKG-004",
    "PKG-005",
    "PKG-009",
    "PKG-011",
    "PKG-012",
    "PKG-013",
    "PKG-016",
    "PKG-017",
    "PKG-018",
    "PKG-019",
    "PKG-021",
    "PKG-022",
    "PKG-023",
    "PKG-024",
    "PKG-025",
    "PKG-026",
    "PKG-027",
    "PKG-028",
    "PKG-029",
    "PKG-030",
    "PKG-031",
    "PKG-032",
    "FIN-001",
    "FIN-002",
    "FIN-003",
    "FIN-004",
    "FIN-005",
    "FIN-006",
    "FIN-007",
    "FIN-008",
)
PLACEHOLDER_TOKEN_RE = re.compile(
    r"(?:\b(?:todo|tbd|placeholder|replace(?:_|-)?me|changeme)\b|example\.com|\.example\b|yyyy)",
    flags=re.IGNORECASE,
)
