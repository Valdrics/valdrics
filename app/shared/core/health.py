"""
Enhanced Health Check System

Provides comprehensive health monitoring for all system components,
including databases, caches, external services, and circuit breakers.
"""

import asyncio
from collections.abc import Awaitable
import psutil  # noqa: F401 - retained for tests that monkeypatch psutil symbols
import structlog
from typing import Any, Dict, List
from datetime import datetime, timezone, timedelta
from httpx import HTTPError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.core.config import get_settings
from app.shared.core.system_resources import (
    safe_cpu_percent,
    safe_virtual_memory,
    safe_disk_usage,
)
from app.shared.core.health_check_ops import (
    evaluate_background_jobs,
    evaluate_system_resources,
)
from app.shared.core.circuit_breaker import get_all_circuit_breakers
from app.shared.db.session import health_check as db_health_check
from app.shared.core.cache import get_cache_service
from app.shared.core.async_utils import maybe_await

logger = structlog.get_logger()
settings = get_settings()
HEALTH_RECOVERABLE_ERRORS = (
    SQLAlchemyError,
    HTTPError,
    RuntimeError,
    OSError,
    TimeoutError,
    ImportError,
    AttributeError,
    TypeError,
    ValueError,
    asyncio.TimeoutError,
)
HEALTH_FALLBACK_STATUSES: dict[str, str] = {
    "database": "down",
    "cache": "unhealthy",
    "external_services": "degraded",
    "circuit_breakers": "unknown",
    "system_resources": "unknown",
    "background_jobs": "unknown",
}


class HealthService:
    """Comprehensive health check service for all system components."""

    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    async def check_all(self) -> Dict[str, Any]:
        """Run system health checks and return a lifecycle-friendly payload."""
        health = await self.comprehensive_health_check()

        # Format for tests which expect specific keys at root
        # and 'up'/'down' status for the database
        return {
            "status": health["status"],
            "timestamp": health["timestamp"],
            "database": health["checks"]["database"],
            "redis": health["checks"]["cache"],  # Tests expect 'redis' key
            "aws": health["checks"]["external_services"]["services"].get(
                "aws_sts", {"status": "unknown"}
            ),
            "system": health["checks"]["system_resources"],
            "checks": health["checks"],
        }

    async def check_database(self) -> tuple[bool, Dict[str, Any]]:
        """Public method for checking database status, return (is_healthy, details)."""
        status = await self._check_database()
        return status["status"] == "up", status

    async def check_redis(self) -> tuple[bool, Dict[str, Any]]:
        """Public method for checking redis status, return (is_healthy, details)."""
        try:
            from app.shared.core.rate_limit import get_redis_client

            settings = get_settings()

            if not settings.REDIS_URL:
                return True, {"status": "skipped"}

            client = get_redis_client()
            if not client:
                return False, {"error": "Redis client not available"}

            await maybe_await(client.ping())
            return True, {"latency_ms": 0}  # Could measure actual latency

        except HEALTH_RECOVERABLE_ERRORS as e:
            return False, {"error": str(e)}

    async def check_aws(self) -> tuple[bool, Dict[str, Any]]:
        """Public method for checking AWS connectivity, return (is_reachable, details)."""
        try:
            from app.shared.core.http import get_http_client

            client = get_http_client()
            response = await client.get("https://sts.amazonaws.com")

            if response.status_code < 400:
                return True, {"reachable": True}
            elif response.status_code < 500:
                # Client errors (4xx) still mean the service is reachable
                return True, {"reachable": True}
            else:
                # Server errors (5xx) mean unreachable
                return False, {"error": f"STS returned {response.status_code}"}

        except HEALTH_RECOVERABLE_ERRORS as e:
            return False, {"error": str(e)}

    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """
        Performs comprehensive health check of all system components.

        Returns detailed health status for monitoring and alerting.
        """
        component_checks = (
            (
                "database",
                self._run_health_check(
                    self._check_database(),
                    component="database",
                ),
            ),
            (
                "cache",
                self._run_health_check(
                    self._check_cache(),
                    component="cache",
                ),
            ),
            (
                "external_services",
                self._run_health_check(
                    self._check_external_services(),
                    component="external_services",
                ),
            ),
            (
                "circuit_breakers",
                self._run_health_check(
                    self._check_circuit_breakers(),
                    component="circuit_breakers",
                ),
            ),
            (
                "system_resources",
                self._run_health_check(
                    self._check_system_resources(),
                    component="system_resources",
                ),
            ),
            (
                "background_jobs",
                self._run_health_check(
                    self._check_background_jobs(),
                    component="background_jobs",
                ),
            ),
        )
        gathered_checks = await asyncio.gather(
            *(coro for _, coro in component_checks),
            return_exceptions=True,
        )
        checks = [
            self._normalize_health_check_result(component=component, result=result)
            for (component, _), result in zip(component_checks, gathered_checks)
        ]

        # Unpack results
        (
            db_status,
            cache_status,
            external_status,
            circuit_status,
            system_status,
            jobs_status,
        ) = checks

        # Determine overall health
        overall_status = self._calculate_overall_health(
            [
                db_status,
                cache_status,
                external_status,
                circuit_status,
                system_status,
                jobs_status,
            ]
        )

        health_data = {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "database": db_status,
                "cache": cache_status,
                "external_services": external_status,
                "circuit_breakers": circuit_status,
                "system_resources": system_status,
                "background_jobs": jobs_status,
            },
            "version": getattr(settings, "VERSION", "unknown"),
            "environment": getattr(settings, "ENVIRONMENT", "unknown"),
        }

        # Log health check results
        if overall_status == "unhealthy":
            logger.error("health_check_failed", health_data=health_data)
        elif overall_status == "degraded":
            logger.warning("health_check_degraded", health_data=health_data)
        else:
            logger.debug("health_check_passed", status=overall_status)

        return health_data

    async def _run_health_check(
        self,
        coro: Awaitable[Dict[str, Any]],
        *,
        component: str,
    ) -> Dict[str, Any]:
        """Contain unexpected subcheck failures so /health remains deterministic."""
        try:
            result = await coro
        except HEALTH_RECOVERABLE_ERRORS as exc:
            fallback_status = HEALTH_FALLBACK_STATUSES.get(component, "unknown")
            logger.error(
                "health_check_unhandled_exception",
                component=component,
                fallback_status=fallback_status,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return {
                "status": fallback_status,
                "error": str(exc),
                "component": component,
            }

        return self._normalize_health_check_result(component=component, result=result)

    def _normalize_health_check_result(
        self,
        *,
        component: str,
        result: Dict[str, Any] | Exception | BaseException,
    ) -> Dict[str, Any]:
        if isinstance(result, BaseException) and not isinstance(result, Exception):
            raise result

        if isinstance(result, Exception):
            fallback_status = HEALTH_FALLBACK_STATUSES.get(component, "unknown")
            logger.error(
                "health_check_unhandled_exception",
                component=component,
                fallback_status=fallback_status,
                error_type=type(result).__name__,
                error=str(result),
            )
            return {
                "status": fallback_status,
                "error": str(result),
                "component": component,
            }

        if not isinstance(result, dict):
            logger.error(
                "health_check_invalid_payload",
                component=component,
                payload_type=type(result).__name__,
            )
            return {
                "status": HEALTH_FALLBACK_STATUSES.get(component, "unknown"),
                "error": "Health check returned non-dict payload",
                "component": component,
            }
        return result

    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            # db_health_check is imported from session.py
            db_health = await db_health_check()
            return db_health

        except HEALTH_RECOVERABLE_ERRORS as e:
            logger.error("database_health_check_failed", error=str(e))
            return {"status": "down", "error": str(e), "component": "database"}

    async def _check_cache(self) -> Dict[str, Any]:
        """Check cache service health."""
        try:
            cache = get_cache_service()

            if not cache.enabled:
                return {"status": "disabled", "message": "Cache service not configured"}

            # Simple cache health check
            test_key = f"health_check_{asyncio.get_event_loop().time()}"
            test_value = "ok"

            # Test set and get
            set_success = await cache.set(
                test_key, test_value, ttl=timedelta(seconds=10)
            )
            get_value = await cache.get(test_key)

            if set_success and get_value == test_value:
                return {
                    "status": "healthy",
                    "latency_ms": 0,
                }  # Could measure actual latency
            else:
                return {"status": "unhealthy", "message": "Cache set/get failed"}

        except HEALTH_RECOVERABLE_ERRORS as e:
            logger.error("cache_health_check_failed", error=str(e))
            return {"status": "unhealthy", "error": str(e), "component": "cache"}

    async def _check_external_services(self) -> Dict[str, Any]:
        """Check external service connectivity."""
        services_status = {}

        try:
            from app.shared.core.http import get_http_client

            client = get_http_client()
            response = await client.get("https://sts.amazonaws.com")
            services_status["aws_sts"] = {
                "status": "healthy" if response.status_code < 500 else "unhealthy",
                "response_code": response.status_code,
            }
        except HEALTH_RECOVERABLE_ERRORS as e:
            services_status["aws_sts"] = {"status": "unhealthy", "error": str(e)}

        # Check other external services as needed
        # Add checks for LLM providers, webhooks, etc.

        all_healthy = all(
            service.get("status") == "healthy" for service in services_status.values()
        )

        return {
            "status": "healthy" if all_healthy else "degraded",
            "services": services_status,
        }

    async def _check_circuit_breakers(self) -> Dict[str, Any]:
        """Check circuit breaker status."""
        try:
            circuit_breakers = get_all_circuit_breakers()

            if not circuit_breakers:
                return {
                    "status": "healthy",
                    "message": "No circuit breakers configured",
                }

            # Check if any circuit breakers are in open state
            open_breakers = [
                name
                for name, status in circuit_breakers.items()
                if status.get("state") == "open"
            ]

            if open_breakers:
                return {
                    "status": "degraded",
                    "message": f"Circuit breakers open: {', '.join(open_breakers)}",
                    "open_breakers": open_breakers,
                    "all_breakers": circuit_breakers,
                }

            return {
                "status": "healthy",
                "circuit_breakers": len(circuit_breakers),
                "all_closed": True,
            }

        except HEALTH_RECOVERABLE_ERRORS as e:
            logger.error("circuit_breaker_health_check_failed", error=str(e))
            return {"status": "unknown", "error": str(e)}

    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        result = evaluate_system_resources(
            virtual_memory_sampler=safe_virtual_memory,
            cpu_percent_sampler=safe_cpu_percent,
            disk_usage_sampler=safe_disk_usage,
            recoverable_errors=HEALTH_RECOVERABLE_ERRORS,
        )
        if result.get("status") == "unknown" and result.get("error"):
            logger.error(
                "system_resources_health_check_failed",
                error=str(result.get("error")),
            )
        return result

    async def _check_background_jobs(self) -> Dict[str, Any]:
        """Check background job queue health."""
        result = await evaluate_background_jobs(
            db=self.db,
            recoverable_errors=HEALTH_RECOVERABLE_ERRORS,
        )
        if result.get("status") == "unknown" and result.get("error"):
            logger.error("background_jobs_health_check_failed", error=str(result["error"]))
        return result

    def _calculate_overall_health(self, check_results: List[Dict[str, Any]]) -> str:
        """Calculate overall health status from individual checks."""
        if any(check.get("status") in ["unhealthy", "down"] for check in check_results):
            return "unhealthy"

        if any(check.get("status") == "degraded" for check in check_results):
            return "degraded"

        if all(
            check.get("status") in ["healthy", "up", "disabled"]
            for check in check_results
        ):
            return "healthy"

        return "unknown"

    async def _handle_check_errors(
        self, coro: Awaitable[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Handle errors in individual health checks."""
        try:
            result = await coro
            return result
        except HEALTH_RECOVERABLE_ERRORS as e:
            logger.error("health_check_error", error=str(e))
            return {"status": "error", "error": str(e)}


async def get_health_status(db: AsyncSession | None = None) -> Dict[str, Any]:
    """Get comprehensive health status for monitoring."""
    service = HealthService(db)
    return await service.comprehensive_health_check()
