from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CATEGORY_MAPPING: dict[str, str] = {
    "unattached_azure_disks": "unattached_volumes",
    "unattached_gcp_disks": "unattached_volumes",
    "unattached_disks": "unattached_volumes",
    "orphan_azure_ips": "unused_elastic_ips",
    "orphan_gcp_ips": "unused_elastic_ips",
    "orphaned_ips": "unused_elastic_ips",
    "idle_azure_vms": "idle_instances",
    "idle_azure_gpu_vms": "idle_instances",
    "idle_gcp_vms": "idle_instances",
    "idle_gcp_gpu_instances": "idle_instances",
    "old_azure_snapshots": "old_snapshots",
    "old_gcp_snapshots": "old_snapshots",
    "idle_azure_sql": "idle_rds_databases",
    "idle_gcp_cloud_sql": "idle_rds_databases",
    "idle_azure_aks": "idle_container_clusters",
    "empty_gke_clusters": "idle_container_clusters",
    "unused_azure_app_service_plans": "unused_app_service_plans",
    "idle_cloud_run": "idle_serverless_services",
    "idle_cloud_functions": "idle_serverless_functions",
    "orphan_azure_nics": "orphan_network_components",
    "orphan_azure_nsgs": "orphan_network_components",
}


def _initial_scan_payload(scanned_connections: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "unattached_volumes": [],
        "old_snapshots": [],
        "unused_elastic_ips": [],
        "idle_instances": [],
        "orphan_load_balancers": [],
        "idle_rds_databases": [],
        "underused_nat_gateways": [],
        "idle_s3_buckets": [],
        "stale_ecr_images": [],
        "idle_sagemaker_endpoints": [],
        "cold_redshift_clusters": [],
        "idle_saas_subscriptions": [],
        "unused_license_seats": [],
        "idle_platform_services": [],
        "idle_hybrid_resources": [],
        "idle_container_clusters": [],
        "unused_app_service_plans": [],
        "idle_serverless_services": [],
        "idle_serverless_functions": [],
        "orphan_network_components": [],
        "errors": [],
        "scanned_connections": scanned_connections,
        "partial_results": False,
        "scan_completeness": [],
    }
    return payload


@dataclass
class ZombieScanState:
    payload: dict[str, Any]
    total_waste: float
    has_precision: bool
    has_attribution: bool

    @classmethod
    def create(
        cls,
        *,
        scanned_connections: int,
        has_precision: bool,
        has_attribution: bool,
    ) -> "ZombieScanState":
        return cls(
            payload=_initial_scan_payload(scanned_connections),
            total_waste=0.0,
            has_precision=has_precision,
            has_attribution=has_attribution,
        )

    def merge_scan_results(
        self,
        *,
        provider_name: str,
        connection_id: str,
        connection_name: str,
        scan_results: dict[str, Any],
        region_override: str | None = None,
    ) -> None:
        for category, items in scan_results.items():
            if not isinstance(items, list):
                continue
            ui_key = CATEGORY_MAPPING.get(category, category)
            bucket = self.payload.setdefault(ui_key, [])
            for item in items:
                if not isinstance(item, dict):
                    continue
                res_id = item.get("resource_id") or item.get("id")
                cost = float(item.get("monthly_cost") or item.get("monthly_waste") or 0)
                normalized_region = region_override or item.get("region") or item.get("zone")
                item.update(
                    {
                        "provider": provider_name,
                        "connection_id": connection_id,
                        "connection_name": connection_name,
                        "resource_id": res_id,
                        "monthly_cost": cost,
                        "is_gpu": (
                            bool(item.get("is_gpu", False))
                            if self.has_precision
                            else "Growth Plan Required"
                        ),
                        "owner": (
                            item.get("owner", "unknown")
                            if self.has_attribution
                            else "Growth Plan Required"
                        ),
                    }
                )
                if normalized_region:
                    item["region"] = normalized_region
                bucket.append(item)
                self.total_waste += cost

        completeness = scan_results.get("scan_completeness")
        if isinstance(completeness, dict):
            plugins = completeness.get("plugins")
            connection_region = region_override or completeness.get("region") or "global"
            inventory_discovery = completeness.get("inventory_discovery")
            summary = {
                "provider": provider_name,
                "connection_id": connection_id,
                "connection_name": connection_name,
                "region": connection_region,
                "degraded": bool(completeness.get("degraded", False)),
                "error_count": int(completeness.get("error_count", 0) or 0),
                "plugins": plugins if isinstance(plugins, dict) else {},
                "inventory_discovery": (
                    dict(inventory_discovery)
                    if isinstance(inventory_discovery, dict)
                    else {}
                ),
            }
            self.payload["scan_completeness"].append(summary)
            if summary["degraded"]:
                self.payload["partial_results"] = True
                plugins_summary = summary.get("plugins")
                if isinstance(plugins_summary, dict):
                    for plugin_key, plugin_metadata in plugins_summary.items():
                        if not isinstance(plugin_metadata, dict):
                            continue
                        if str(plugin_metadata.get("status") or "ok") == "ok":
                            continue
                        self.payload["errors"].append(
                            {
                                "provider": provider_name,
                                "region": connection_region,
                                "error": str(plugin_metadata.get("error") or "unknown"),
                                "error_type": str(
                                    plugin_metadata.get("error_type") or "unknown"
                                ),
                                "connection_id": connection_id,
                                "category": str(plugin_key),
                                "status": str(plugin_metadata.get("status") or "failed"),
                            }
                        )
                inventory_summary = summary.get("inventory_discovery")
                if isinstance(inventory_summary, dict):
                    inventory_status = str(inventory_summary.get("status") or "ok")
                    if inventory_status != "ok":
                        self._mark_connection_items_manual_review(
                            provider_name=provider_name,
                            connection_id=connection_id,
                            connection_region=connection_region,
                            inventory_summary=inventory_summary,
                        )
                        self.payload["errors"].append(
                            {
                                "provider": provider_name,
                                "region": connection_region,
                                "error": str(
                                    inventory_summary.get("coverage_limitations")
                                    or "Inventory discovery is partial or degraded"
                                ),
                                "error_type": "InventoryDiscoveryPartial",
                                "connection_id": connection_id,
                                "category": "inventory_discovery",
                                "status": inventory_status,
                            }
                        )

            overall_error = completeness.get("overall_error")
            if overall_error:
                self.payload["partial_results"] = True
                self.payload["errors"].append(
                    {
                        "provider": provider_name,
                        "region": connection_region,
                        "error": str(overall_error),
                        "connection_id": connection_id,
                        "category": "scan",
                        "status": "failed",
                    }
                )

        top_level_error = scan_results.get("error")
        if top_level_error:
            self.payload["partial_results"] = True
            self.payload["errors"].append(
                {
                    "provider": provider_name,
                    "region": region_override or scan_results.get("region") or "global",
                    "error": str(top_level_error),
                    "connection_id": connection_id,
                    "category": "scan",
                    "status": "failed",
                }
            )

    def _mark_connection_items_manual_review(
        self,
        *,
        provider_name: str,
        connection_id: str,
        connection_region: str,
        inventory_summary: dict[str, Any],
    ) -> None:
        inventory_status = str(inventory_summary.get("status") or "partial")
        inventory_note = str(
            inventory_summary.get("coverage_limitations")
            or "Inventory discovery is partial or degraded; manual review is required."
        )
        for category, bucket in self.payload.items():
            if category in {"errors", "scan_completeness"}:
                continue
            if not isinstance(bucket, list):
                continue
            for item in bucket:
                if not isinstance(item, dict):
                    continue
                if str(item.get("provider") or "") != provider_name:
                    continue
                if str(item.get("connection_id") or "") != connection_id:
                    continue
                item_region = str(item.get("region") or connection_region or "global")
                if connection_region not in {"", "global"} and item_region != connection_region:
                    continue
                item["requires_manual_review"] = True
                item["automated_action_allowed"] = False
                item["decision_gate"] = "manual_review_required"
                item["inventory_discovery_status"] = inventory_status
                item["inventory_discovery_note"] = inventory_note
                notes = str(item.get("explainability_notes") or "").strip()
                if inventory_note not in notes:
                    item["explainability_notes"] = (
                        f"{notes} Manual review required because {inventory_note}".strip()
                    )

    def append_error(
        self,
        *,
        provider: str,
        region: str,
        error: str,
        connection_id: str,
    ) -> None:
        self.payload["partial_results"] = True
        self.payload["errors"].append(
            {
                "provider": provider,
                "region": region,
                "error": error,
                "connection_id": connection_id,
            }
        )

    @staticmethod
    def connection_display_name(connection: Any) -> str:
        for attr in ("name", "vendor", "subscription_id", "project_id", "aws_account_id"):
            raw = getattr(connection, attr, None)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
        connection_id = getattr(connection, "id", None)
        return str(connection_id) if connection_id is not None else "connection"
