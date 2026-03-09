from __future__ import annotations

from typing import Any

import structlog
from botocore.exceptions import BotoCoreError, ClientError

from app.modules.optimization.adapters.common.rightsizing_common import (
    build_rightsizing_finding,
    evaluate_max_samples,
    is_small_shape,
    utc_window,
)
from app.modules.optimization.adapters.aws.plugins.pricing_evidence import (
    build_pricing_fields,
)
from app.modules.optimization.domain.plugin import ZombiePlugin
from app.modules.optimization.domain.registry import registry
from app.modules.reporting.domain.pricing.service import PricingService

logger = structlog.get_logger()

CPU_MAX_THRESHOLD_PERCENT = 10.0
SKIPPED_INSTANCE_TOKENS: tuple[str, ...] = ("nano", "micro")
AWS_RIGHTSIZING_SCAN_RECOVERABLE_EXCEPTIONS = (
    ClientError,
    BotoCoreError,
    OSError,
    TimeoutError,
)


@registry.register("aws")
class OverprovisionedEc2Plugin(ZombiePlugin):
    """Detect running EC2 instances with persistently low peak CPU usage."""

    @property
    def category_key(self) -> str:
        return "overprovisioned_ec2_instances"

    @staticmethod
    def _estimate_pricing_quote(instance_type: str, region: str):
        return PricingService.estimate_monthly_waste_quote(
            provider="aws",
            resource_type="instance",
            resource_size=instance_type,
            region=region,
        )

    async def scan(
        self,
        session: Any,
        region: str,
        credentials: dict[str, Any] | None = None,
        config: Any = None,
        inventory: Any = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        del inventory, kwargs
        findings: list[dict[str, Any]] = []

        try:
            async with self._get_client(
                session,
                "ec2",
                region,
                credentials,
                config=config,
            ) as ec2_client, self._get_client(
                session,
                "cloudwatch",
                region,
                credentials,
                config=config,
            ) as cloudwatch_client:
                paginator = ec2_client.get_paginator("describe_instances")
                async for page in paginator.paginate(
                    Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
                ):
                    reservations = page.get("Reservations", [])
                    for reservation in reservations:
                        for instance in reservation.get("Instances", []):
                            finding = await self._scan_instance(
                                cloudwatch_client=cloudwatch_client,
                                instance=instance,
                                region=region,
                            )
                            if finding is not None:
                                findings.append(finding)
        except AWS_RIGHTSIZING_SCAN_RECOVERABLE_EXCEPTIONS as exc:
            logger.error(
                "aws_rightsizing_scan_error",
                error=str(exc),
                region=region,
            )

        return findings

    async def _scan_instance(
        self,
        *,
        cloudwatch_client: Any,
        instance: dict[str, Any],
        region: str,
    ) -> dict[str, Any] | None:
        instance_id = str(instance.get("InstanceId") or "").strip()
        instance_type = str(instance.get("InstanceType") or "").strip()
        if not instance_id or not instance_type:
            return None
        if is_small_shape(instance_type, tokens=SKIPPED_INSTANCE_TOKENS):
            return None

        start_time, end_time = utc_window(7)
        try:
            stats = await cloudwatch_client.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=["Maximum"],
            )
        except AWS_RIGHTSIZING_SCAN_RECOVERABLE_EXCEPTIONS as exc:
            logger.warning(
                "aws_rightsizing_instance_metric_error",
                instance_id=instance_id,
                error=str(exc),
            )
            return None

        datapoints = stats.get("Datapoints", [])
        evaluation = evaluate_max_samples(
            (
                point.get("Maximum", 0.0)
                for point in datapoints
                if isinstance(point, dict)
            ),
            threshold=CPU_MAX_THRESHOLD_PERCENT,
        )
        if not evaluation.has_data or not evaluation.below_threshold:
            return None

        pricing_quote = self._estimate_pricing_quote(
            instance_type=instance_type,
            region=region,
        )
        estimated_monthly_cost = round(float(pricing_quote.monthly_cost_usd), 2)
        if estimated_monthly_cost <= 0.0:
            logger.warning(
                "aws_rightsizing_pricing_unavailable",
                instance_id=instance_id,
                instance_type=instance_type,
                region=region,
                pricing_source=pricing_quote.source,
            )
            return None

        finding = build_rightsizing_finding(
            resource_id=instance_id,
            resource_type="AWS EC2 Instance",
            resource_name=self._get_name_tag(instance),
            region=region,
            monthly_cost=estimated_monthly_cost,
            current_size=instance_type,
            max_cpu_percent=evaluation.max_observed,
            threshold_percent=CPU_MAX_THRESHOLD_PERCENT,
            action="resize_ec2_instance",
            confidence_score=0.85,
        )
        finding.update(build_pricing_fields(pricing_quote))
        return finding

    def _get_name_tag(self, instance: dict[str, Any]) -> str:
        for tag in instance.get("Tags", []):
            if not isinstance(tag, dict):
                continue
            if tag.get("Key") == "Name":
                return str(tag.get("Value") or "")
        return str(instance.get("InstanceId", "unknown"))
