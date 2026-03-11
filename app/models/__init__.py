"""
Model package initializer.

This module exists to make sure SQLAlchemy's registry is populated in any runtime
that uses the ORM outside of `app/main.py` (scripts, workers, one-off jobs).
"""

from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Mapper, configure_mappers

from app.shared.db.base import Base

# Import side-effects: register ORM mappings.
from app.models import (  # noqa: F401
    anomaly_marker,
    attribution,
    aws_connection,
    azure_connection,
    background_job,
    carbon_factors,
    carbon_settings,
    cloud,
    cost_audit,
    discovery_candidate,
    discovered_account,
    enforcement,
    enforcement_approval_models,
    enforcement_decision_models,
    enforcement_policy_models,
    gcp_connection,
    hybrid_connection,
    invoice,
    license_connection,
    landing_telemetry_rollup,
    llm,
    notification_settings,
    optimization,
    platform_connection,
    pricing,
    public_sales_inquiry,
    realized_savings,
    remediation,
    remediation_settings,
    saas_connection,
    scim_group,
    security,
    sso_domain_mapping,
    tenant,
    tenant_growth_funnel_snapshot,
    tenant_identity_settings,
    unit_economics_settings,
)
from app.modules.governance.domain.security import audit_log as governance_audit_log  # noqa: F401


def _apply_relationship_loader_policy() -> None:
    """
    Force non-N+1 defaults across ORM relationships.

    We upgrade SQLAlchemy's implicit ``lazy='select'`` strategy to ``raise_on_sql``
    for all mapped relationships unless a model explicitly opts into a different
    loader strategy. This fail-fast policy prevents accidental N+1 query patterns
    from shipping silently.
    """

    configure_mappers()
    for mapper in Base.registry.mappers:
        for relation in mapper.relationships:
            if relation.lazy == "select":
                relation.lazy = "raise_on_sql"


@event.listens_for(Mapper, "mapper_configured")
def _on_mapper_configured(mapper: Mapper[Any], _class: type[object]) -> None:
    for relation in mapper.relationships:
        if relation.lazy == "select":
            relation.lazy = "raise_on_sql"


_apply_relationship_loader_policy()
