import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable, Awaitable
from uuid import UUID
from httpx import HTTPError
import structlog
import time
from sqlalchemy import select  # noqa: F401
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from app.shared.core.service import BaseService

from app.modules.optimization.domain.architectural_inefficiency import (
    build_architectural_inefficiency_payload,
)
from app.modules.optimization.domain.factory import ZombieDetectorFactory
from app.modules.optimization.domain.strategy_service import OptimizationService
from app.modules.optimization.domain.waste_rightsizing import (
    build_waste_rightsizing_payload,
)
from app.modules.optimization.domain.zombie_scan_state import ZombieScanState
from app.shared.core.connection_queries import CONNECTION_MODEL_PAIRS
from app.shared.core.connection_state import resolve_connection_region
from app.shared.core.provider import normalize_provider, resolve_provider_from_connection
from app.shared.core.pricing import PricingTier, FeatureFlag, is_feature_enabled

logger = structlog.get_logger()
__all__ = ["ZombieService", "OptimizationService"]


async def enqueue_zombie_analysis(
    *,
    db: Any,
    tenant_id: UUID,
    all_zombies: dict[str, Any],
    requested_by_user_id: UUID | None,
    requested_client_ip: str | None,
    recoverable_errors: tuple[type[Exception], ...],
    logger: Any,
) -> dict[str, Any]:
    from sqlalchemy.dialects.postgresql import insert

    from app.models.background_job import BackgroundJob, JobStatus, JobType

    now = datetime.now(timezone.utc)
    job_id = None
    try:
        bucket_str = now.strftime("%Y-%m-%d-%H")
        dedup_key = f"{tenant_id}:zombie_analysis:{bucket_str}"
        stmt = (
            insert(BackgroundJob)
            .values(
                job_type=JobType.ZOMBIE_ANALYSIS.value,
                tenant_id=tenant_id,
                status=JobStatus.PENDING,
                scheduled_for=now,
                created_at=now,
                deduplication_key=dedup_key,
                payload={
                    "zombies": all_zombies,
                    "requested_by_user_id": (
                        str(requested_by_user_id) if requested_by_user_id else None
                    ),
                    "requested_client_ip": requested_client_ip,
                },
            )
            .on_conflict_do_nothing(index_elements=["deduplication_key"])
            .returning(BackgroundJob.id)
        )

        result = await db.execute(stmt)
        job_id = result.scalar_one_or_none()
        await db.commit()

        if job_id:
            from app.shared.core.ops_metrics import BACKGROUND_JOBS_ENQUEUED

            BACKGROUND_JOBS_ENQUEUED.labels(
                job_type=JobType.ZOMBIE_ANALYSIS.value,
                priority="normal",
            ).inc()

        return {
            "status": "pending",
            "job_id": str(job_id) if job_id else "already_queued",
            "summary": "AI Analysis has been queued and will be available shortly.",
        }
    except recoverable_errors as exc:
        logger.error("failed_to_enqueue_ai_analysis", error=str(exc))
        return {"status": "error", "error": "Failed to queue analysis"}

ZOMBIE_CONNECTION_QUERY_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    SQLAlchemyError,
    RuntimeError,
    OSError,
    TimeoutError,
    TypeError,
    ValueError,
)
ZOMBIE_SCAN_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    HTTPError,
    RuntimeError,
    OSError,
    TimeoutError,
    TypeError,
    ValueError,
    KeyError,
    AttributeError,
)
ZOMBIE_AI_ENQUEUE_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    SQLAlchemyError,
    RuntimeError,
    OSError,
    TimeoutError,
    TypeError,
    ValueError,
)
ZOMBIE_AI_ANALYSIS_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    RuntimeError,
    OSError,
    TimeoutError,
    ImportError,
    AttributeError,
    TypeError,
    ValueError,
)
ZOMBIE_NOTIFICATION_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    RuntimeError,
    OSError,
    TimeoutError,
    ImportError,
    AttributeError,
    TypeError,
    ValueError,
    Exception,
)

class ZombieService(BaseService):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def _load_connections_for_model(
        self, model: Any, tenant_id: UUID
    ) -> list[Any]:
        try:
            stmt = self._scoped_query(model, tenant_id)
            if hasattr(model, "status"):
                stmt = stmt.where(model.status == "active")
            elif hasattr(model, "is_active"):
                stmt = stmt.where(model.is_active.is_(True))
            q = await self.db.execute(stmt)
            return list(q.scalars().all())
        except (StopIteration, StopAsyncIteration):
            logger.debug(
                "zombie_scan_mocked_query_exhausted",
                model=getattr(model, "__name__", str(model)),
                tenant_id=str(tenant_id),
            )
            return []
        except ZOMBIE_CONNECTION_QUERY_RECOVERABLE_ERRORS as exc:
            logger.warning(
                "zombie_scan_connection_query_failed",
                model=getattr(model, "__name__", str(model)),
                tenant_id=str(tenant_id),
                error=str(exc),
            )
            return []

    async def scan_for_tenant(
        self,
        tenant_id: UUID,
        region: str = "global",
        analyze: bool = False,
        requested_by_user_id: UUID | None = None,
        requested_client_ip: str | None = None,
        on_category_complete: Optional[
            Callable[[str, List[Dict[str, Any]]], Awaitable[None]]
        ] = None,
    ) -> Dict[str, Any]:
        region = str(region or "").strip() or "global"
        all_connections: list[Any] = []
        connection_models = [model for _provider, model in CONNECTION_MODEL_PAIRS]
        for model in connection_models:
            all_connections.extend(
                await self._load_connections_for_model(model, tenant_id)
            )

        if not all_connections:
            return {
                "resources": {},
                "total_monthly_waste": 0.0,
                "error": "No cloud connections found.",
            }

        from app.shared.core.pricing import get_tenant_tier

        tier = await get_tenant_tier(tenant_id, self.db)
        has_precision = is_feature_enabled(tier, FeatureFlag.PRECISION_DISCOVERY)
        has_attribution = is_feature_enabled(tier, FeatureFlag.OWNER_ATTRIBUTION)
        scan_state = ZombieScanState.create(
            scanned_connections=len(all_connections),
            has_precision=has_precision,
            has_attribution=has_attribution,
        )
        all_zombies = scan_state.payload

        async def run_scan(
            conn: Any,
        ) -> None:
            provider = normalize_provider(resolve_provider_from_connection(conn))
            connection_name = ZombieScanState.connection_display_name(conn)
            connection_region = resolve_connection_region(conn)
            try:
                if provider == "aws":
                    from app.modules.optimization.adapters.aws.region_discovery import (
                        RegionDiscovery,
                    )

                    explicit_region = region if region != "global" else connection_region

                    temp_detector = ZombieDetectorFactory.get_detector(
                        conn, region=explicit_region, db=self.db
                    )
                    raw_credentials = (
                        await temp_detector.get_credentials()
                        if hasattr(temp_detector, "get_credentials")
                        else None
                    )
                    credentials: dict[str, str] | None
                    if isinstance(raw_credentials, dict):
                        credentials = {
                            str(k): str(v)
                            for k, v in raw_credentials.items()
                            if v is not None
                        }
                    else:
                        credentials = None
                    if region != "global":
                        enabled_regions = [region]
                    else:
                        rd = RegionDiscovery(credentials=credentials)
                        enabled_regions = await rd.get_enabled_regions()
                    if not enabled_regions:
                        fallback_region = connection_region
                        if fallback_region == "global":
                            from app.shared.core.config import get_settings

                            fallback_region = (
                                str(get_settings().AWS_DEFAULT_REGION or "").strip()
                                or "us-east-1"
                            )
                        enabled_regions = [fallback_region]

                    logger.info(
                        "aws_parallel_scan_starting",
                        tenant_id=str(tenant_id),
                        region_count=len(enabled_regions),
                    )

                    async def scan_single_region(reg: str) -> None:
                        try:
                            regional_detector = ZombieDetectorFactory.get_detector(
                                conn, region=reg, db=self.db
                            )
                            reg_results = await regional_detector.scan_all(
                                on_category_complete=on_category_complete
                            )
                            scan_state.merge_scan_results(
                                provider_name=regional_detector.provider_name,
                                connection_id=str(conn.id),
                                connection_name=connection_name,
                                scan_results=reg_results,
                                region_override=reg,
                            )
                        except ZOMBIE_SCAN_RECOVERABLE_ERRORS as exc:
                            logger.error(
                                "regional_scan_failed", region=reg, error=str(exc)
                            )
                            scan_state.append_error(
                                provider="aws",
                                region=reg,
                                error=str(exc),
                                connection_id=str(conn.id),
                            )

                    await asyncio.gather(
                        *(scan_single_region(r) for r in enabled_regions)
                    )
                else:
                    scan_region = region if region != "global" else connection_region
                    detector = ZombieDetectorFactory.get_detector(
                        conn, region=scan_region, db=self.db
                    )
                    results = await detector.scan_all(
                        on_category_complete=on_category_complete
                    )
                    scan_state.merge_scan_results(
                        provider_name=detector.provider_name,
                        connection_id=str(conn.id),
                        connection_name=connection_name,
                        scan_results=results,
                        region_override=scan_region if scan_region != "global" else None,
                    )
            except ZOMBIE_SCAN_RECOVERABLE_ERRORS as exc:
                provider_for_error = (
                    provider
                    or normalize_provider(resolve_provider_from_connection(conn))
                    or type(conn).__name__.replace("Connection", "").lower()
                )
                logger.error(
                    "scan_provider_failed",
                    error=str(exc),
                    provider=provider_for_error,
                    connection_id=str(getattr(conn, "id", "")),
                )
                scan_state.append_error(
                    provider=provider_for_error,
                    region="global",
                    error=str(exc),
                    connection_id=str(getattr(conn, "id", "")),
                )

        from app.shared.core.ops_metrics import SCAN_LATENCY, SCAN_TIMEOUTS

        start_time = time.perf_counter()
        try:
            await asyncio.wait_for(
                asyncio.gather(*(run_scan(c) for c in all_connections)),
                timeout=300,
            )
            latency = time.perf_counter() - start_time
            SCAN_LATENCY.labels(provider="multi", region="aggregated").observe(latency)
        except asyncio.TimeoutError:
            logger.error("scan_overall_timeout", tenant_id=str(tenant_id))
            all_zombies["scan_timeout"] = True
            all_zombies["partial_results"] = True
            SCAN_TIMEOUTS.labels(level="overall", provider="multi").inc()

        all_zombies["total_monthly_waste"] = round(scan_state.total_waste, 2)
        all_zombies["waste_rightsizing"] = build_waste_rightsizing_payload(all_zombies)
        all_zombies["architectural_inefficiency"] = (
            build_architectural_inefficiency_payload(all_zombies)
        )

        if analyze and not all_zombies.get("scan_timeout"):
            all_zombies["ai_analysis"] = await enqueue_zombie_analysis(
                db=self.db,
                tenant_id=tenant_id,
                all_zombies=all_zombies,
                requested_by_user_id=requested_by_user_id,
                requested_client_ip=requested_client_ip,
                recoverable_errors=ZOMBIE_AI_ENQUEUE_RECOVERABLE_ERRORS,
                logger=logger,
            )

        await self._send_notifications(all_zombies, tenant_id)

        return all_zombies

    async def _enrich_with_ai(
        self, zombies: Dict[str, Any], tenant_id: Any, tier: PricingTier
    ) -> None:
        try:
            if not is_feature_enabled(tier, FeatureFlag.LLM_ANALYSIS):
                zombies["ai_analysis"] = {
                    "error": "AI Insights is not available on your current plan.",
                    "summary": "Upgrade to unlock AI-powered analysis.",
                    "upgrade_required": True,
                }
            else:
                from app.shared.llm.factory import LLMFactory
                from app.shared.llm.zombie_analyzer import ZombieAnalyzer

                llm = LLMFactory.create()
                analyzer = ZombieAnalyzer(llm)

                ai_analysis = await analyzer.analyze(
                    detection_results=zombies,
                    tenant_id=tenant_id,
                    db=self.db,
                )
                zombies["ai_analysis"] = ai_analysis
                logger.info("service_zombie_ai_analysis_complete")
        except ZOMBIE_AI_ANALYSIS_RECOVERABLE_ERRORS as exc:
            logger.error("service_zombie_ai_analysis_failed", error=str(exc))
            zombies["ai_analysis"] = {
                "error": f"AI analysis failed: {str(exc)}",
                "summary": "AI analysis unavailable. Rule-based detection completed.",
            }

    async def _send_notifications(
        self, zombies: Dict[str, Any], tenant_id: UUID
    ) -> None:
        try:
            from app.shared.core.notifications import NotificationDispatcher

            estimated_savings = zombies.get("total_monthly_waste", 0.0)
            await NotificationDispatcher.notify_zombies(
                zombies,
                estimated_savings,
                tenant_id=str(tenant_id),
                db=self.db,
            )
        except ZOMBIE_NOTIFICATION_RECOVERABLE_ERRORS as exc:
            logger.error("service_zombie_notification_failed", error=str(exc))
