from __future__ import annotations

import time
from typing import Any

import structlog
from google.cloud import aiplatform_v1
from google.cloud import monitoring_v3
from google.oauth2 import service_account  # noqa: F401

from app.modules.optimization.adapters.common import build_google_recoverable_exceptions
from app.modules.optimization.adapters.common.credentials import resolve_gcp_credentials
from app.modules.optimization.adapters.common.sync_bridge import materialize_iterable
from app.modules.optimization.domain.cloud_api_budget import (
    allow_expensive_cloud_api_call,
)
from app.modules.optimization.domain.plugin import ZombiePlugin
from app.modules.optimization.domain.registry import registry

logger = structlog.get_logger()
GCP_VECTOR_SCAN_RECOVERABLE_EXCEPTIONS = build_google_recoverable_exceptions()


@registry.register("gcp")
class IdleVectorSearchPlugin(ZombiePlugin):
    @property
    def category_key(self) -> str:
        return "idle_vector_search_indices"

    async def scan(
        self,
        session: Any,
        region: str,
        credentials: dict[str, Any] | Any | None = None,
        config: Any = None,
        inventory: Any = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        del config, inventory, kwargs
        project_id = str(session)
        target_region = region if region != "global" else "us-central1"
        findings: list[dict[str, Any]] = []

        try:
            gcp_creds = resolve_gcp_credentials(credentials)
            index_endpoint_client = aiplatform_v1.IndexEndpointServiceClient(
                client_options={"api_endpoint": f"{target_region}-aiplatform.googleapis.com"},
                credentials=gcp_creds,
            )
            monitor_client = monitoring_v3.MetricServiceClient(credentials=gcp_creds)
            index_endpoints = await materialize_iterable(
                index_endpoint_client.list_index_endpoints,
                parent=f"projects/{project_id}/locations/{target_region}",
            )
            for index_endpoint in index_endpoints:
                finding = await self._scan_index_endpoint(
                    index_endpoint=index_endpoint,
                    monitor_client=monitor_client,
                    project_id=project_id,
                    target_region=target_region,
                )
                if finding is not None:
                    findings.append(finding)
        except GCP_VECTOR_SCAN_RECOVERABLE_EXCEPTIONS as exc:
            logger.error(
                "gcp_vector_scan_error",
                error=str(exc),
                project_id=project_id,
                region=target_region,
            )

        return findings

    async def _scan_index_endpoint(
        self,
        *,
        index_endpoint: Any,
        monitor_client: monitoring_v3.MetricServiceClient,
        project_id: str,
        target_region: str,
    ) -> dict[str, Any] | None:
        deployed_indexes = getattr(index_endpoint, "deployed_indexes", None) or []
        if not deployed_indexes:
            return None

        endpoint_name = str(getattr(index_endpoint, "name", "") or "").strip()
        if not endpoint_name:
            return None
        endpoint_id = endpoint_name.split("/")[-1]

        allowed = await allow_expensive_cloud_api_call(
            "gcp_monitoring",
            operation="list_time_series",
        )
        if not allowed:
            logger.warning(
                "gcp_monitoring_budget_exhausted",
                plugin=self.category_key,
                index_endpoint_id=endpoint_id,
            )
            return None

        now = int(time.time())
        interval = monitoring_v3.TimeInterval(
            {
                "start_time": {"seconds": now - (7 * 86400)},
                "end_time": {"seconds": now},
            }
        )

        try:
            results = await materialize_iterable(
                monitor_client.list_time_series,
                request={
                    "name": f"projects/{project_id}",
                    "filter": (
                        'metric.type="aiplatform.googleapis.com/index_endpoint/request_count" '
                        f'AND resource.labels.index_endpoint_id="{endpoint_id}"'
                    ),
                    "interval": interval,
                    "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                },
            )
        except GCP_VECTOR_SCAN_RECOVERABLE_EXCEPTIONS as exc:
            logger.warning(
                "gcp_vector_index_metric_error",
                index_endpoint_id=endpoint_id,
                error=str(exc),
            )
            return None

        has_queries = any(getattr(result, "points", None) for result in results)
        if has_queries:
            return None

        endpoint_display_name = str(getattr(index_endpoint, "display_name", "") or endpoint_id)
        return {
            "resource_id": endpoint_name,
            "resource_type": "Vertex AI Vector Index",
            "resource_name": endpoint_display_name,
            "region": target_region,
            "monthly_cost": 500.0,
            "recommendation": "Undeploy unused vector index",
            "action": "undeploy_vector_index",
            "confidence_score": 0.95,
            "explainability_notes": (
                f"Vector Index Endpoint '{endpoint_display_name}' had 0 queries in the last 7 days."
            ),
        }
