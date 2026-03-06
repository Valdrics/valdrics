from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable


def find_idle_eks_clusters(
    *,
    records: list[dict[str, Any]],
    safe_decimal_fn: Callable[[Any], Decimal],
    logger: Any,
    days: int = 7,
) -> list[dict[str, Any]]:
    """Identify EKS clusters based on CUR control-plane charges."""
    eks_usage: dict[str, dict[str, Any]] = {}

    for record in records:
        resource_id = record.get("line_item_resource_id", "")
        product_code = record.get("line_item_product_code", "")

        if product_code != "AmazonEKS":
            continue

        if resource_id not in eks_usage:
            eks_usage[resource_id] = {
                "resource_id": resource_id,
                "total_usage_hours": Decimal("0"),
                "cost": Decimal("0"),
            }

        eks_usage[resource_id]["total_usage_hours"] += safe_decimal_fn(
            record.get("line_item_usage_amount")
        )
        eks_usage[resource_id]["cost"] += safe_decimal_fn(
            record.get("line_item_unblended_cost")
        )

    _ = days
    idle_clusters: list[dict[str, Any]] = []
    for resource_id, data in eks_usage.items():
        if float(data["cost"]) > 50:
            idle_clusters.append(
                {
                    "resource_id": resource_id,
                    "resource_type": "EKS Cluster",
                    "usage_hours": float(data["total_usage_hours"]),
                    "monthly_cost": float(data["cost"]),
                    "recommendation": "EKS cluster detected. Verify workload activity.",
                    "action": "manual_review",
                    "confidence_score": 0.70,
                    "explainability_notes": f"EKS control plane cost: ${data['cost']:.2f}. Review node utilization.",
                    "detection_method": "cur-usage-analysis",
                }
            )

    logger.info(
        "cur_eks_analysis_complete",
        analyzed=len(eks_usage),
        flagged=len(idle_clusters),
    )
    return idle_clusters


__all__ = ["find_idle_eks_clusters"]
