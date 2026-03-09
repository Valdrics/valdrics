import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.shared.core.health import HealthService


@pytest.mark.asyncio
async def test_check_cache_disabled():
    service = HealthService()
    cache = MagicMock()
    cache.enabled = False

    with patch("app.shared.core.health.get_cache_service", return_value=cache):
        result = await service._check_cache()

    assert result["status"] == "disabled"
    assert "not configured" in result["message"]


@pytest.mark.asyncio
async def test_check_cache_set_get_failed():
    service = HealthService()
    cache = MagicMock()
    cache.enabled = True
    cache.set = AsyncMock(return_value=True)
    cache.get = AsyncMock(return_value="wrong")

    with patch("app.shared.core.health.get_cache_service", return_value=cache):
        result = await service._check_cache()

    assert result["status"] == "unhealthy"
    assert "Cache set/get failed" in result["message"]


@pytest.mark.asyncio
async def test_check_external_services_exception():
    service = HealthService()
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(side_effect=RuntimeError("boom"))

    with patch("app.shared.core.http.get_http_client", return_value=mock_client):
        result = await service._check_external_services()

    assert result["status"] == "degraded"
    assert result["services"]["aws_sts"]["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_check_circuit_breakers_none():
    service = HealthService()
    with patch("app.shared.core.health.get_all_circuit_breakers", return_value={}):
        result = await service._check_circuit_breakers()

    assert result["status"] == "healthy"
    assert "No circuit breakers configured" in result["message"]


@pytest.mark.asyncio
async def test_check_circuit_breakers_open():
    service = HealthService()
    breakers = {"aws": {"state": "open"}, "db": {"state": "closed"}}
    with patch(
        "app.shared.core.health.get_all_circuit_breakers", return_value=breakers
    ):
        result = await service._check_circuit_breakers()

    assert result["status"] == "degraded"
    assert "aws" in result["open_breakers"]


@pytest.mark.asyncio
async def test_check_circuit_breakers_exception():
    service = HealthService()
    with patch(
        "app.shared.core.health.get_all_circuit_breakers", side_effect=RuntimeError("oops")
    ):
        result = await service._check_circuit_breakers()

    assert result["status"] == "unknown"
    assert "oops" in result["error"]


@pytest.mark.asyncio
async def test_check_system_resources_degraded():
    service = HealthService()
    memory = SimpleNamespace(percent=90, used=5 * 1024**3, available=1 * 1024**3)
    disk = SimpleNamespace(percent=92, free=2 * 1024**3)

    with (
        patch("app.shared.core.health.safe_virtual_memory", return_value=memory),
        patch("app.shared.core.health.safe_cpu_percent", return_value=95) as mock_cpu,
        patch("app.shared.core.health.safe_disk_usage", return_value=disk) as mock_disk,
    ):
        result = await service._check_system_resources()

    assert result["status"] == "degraded"
    assert "memory_high" in result["warnings"]
    assert "cpu_high" in result["warnings"]
    assert "disk_high" in result["warnings"]
    mock_cpu.assert_called_once_with()
    mock_disk.assert_any_call("/")


@pytest.mark.asyncio
async def test_check_system_resources_exception():
    service = HealthService()
    with patch(
        "app.shared.core.health.psutil.virtual_memory",
        side_effect=RuntimeError("psutil fail"),
    ):
        result = await service._check_system_resources()

    assert result["status"] == "unknown"
    assert "psutil fail" in result["error"]


@pytest.mark.asyncio
async def test_check_background_jobs_no_db():
    service = HealthService(db=None)
    result = await service._check_background_jobs()

    assert result["status"] == "unknown"
    assert "Database session not available" in result["message"]


@pytest.mark.asyncio
async def test_check_background_jobs_stuck_jobs():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 2
    stats = SimpleNamespace(total=2, pending=2, running=0, failed=0)
    stats_result = MagicMock()
    stats_result.first.return_value = stats
    db.execute.side_effect = [mock_result, stats_result]

    service = HealthService(db=db)
    with patch(
        "app.shared.core.health_check_ops._probe_worker_health",
        new=AsyncMock(
            return_value={"status": "healthy", "worker_count": 1, "workers": ["worker@a"]}
        ),
    ):
        result = await service._check_background_jobs()

    assert result["status"] == "degraded"
    assert result["stuck_jobs"] == 2
    assert result["worker_health"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_check_background_jobs_queue_stats():
    db = AsyncMock()
    res_stuck = MagicMock()
    res_stuck.scalar.return_value = 0

    stats = SimpleNamespace(total=5, pending=2, running=1, failed=2)
    res_stats = MagicMock()
    res_stats.first.return_value = stats

    db.execute.side_effect = [res_stuck, res_stats]

    service = HealthService(db=db)
    with patch(
        "app.shared.core.health_check_ops._probe_worker_health",
        new=AsyncMock(
            return_value={"status": "healthy", "worker_count": 1, "workers": ["worker@a"]}
        ),
    ):
        result = await service._check_background_jobs()

    assert result["status"] == "healthy"
    assert result["queue_stats"]["total_jobs"] == 5
    assert result["queue_stats"]["pending_jobs"] == 2
    assert result["worker_health"]["worker_count"] == 1


@pytest.mark.asyncio
async def test_check_background_jobs_exception():
    db = AsyncMock()
    db.execute.side_effect = RuntimeError("db fail")
    service = HealthService(db=db)

    result = await service._check_background_jobs()

    assert result["status"] == "unknown"
    assert "db fail" in result["error"]


@pytest.mark.asyncio
async def test_check_background_jobs_degrades_when_workers_are_not_responding():
    db = AsyncMock()
    stuck_result = MagicMock()
    stuck_result.scalar.return_value = 0
    stats = SimpleNamespace(total=1, pending=0, running=0, failed=0)
    stats_result = MagicMock()
    stats_result.first.return_value = stats
    db.execute.side_effect = [stuck_result, stats_result]

    service = HealthService(db=db)
    with patch(
        "app.shared.core.health_check_ops._probe_worker_health",
        new=AsyncMock(
            return_value={
                "status": "degraded",
                "message": "No Celery workers responded to the heartbeat probe",
                "worker_count": 0,
                "workers": [],
            }
        ),
    ):
        result = await service._check_background_jobs()

    assert result["status"] == "degraded"
    assert result["worker_health"]["worker_count"] == 0


def test_calculate_overall_health_unknown():
    service = HealthService()
    status = service._calculate_overall_health([{"status": "unknown"}])
    assert status == "unknown"


@pytest.mark.asyncio
async def test_handle_check_errors():
    service = HealthService()

    async def boom():
        raise RuntimeError("boom")

    result = await service._handle_check_errors(boom())
    assert result["status"] == "error"
    assert "boom" in result["error"]


@pytest.mark.asyncio
async def test_comprehensive_health_check_contains_unexpected_subcheck_exceptions():
    service = HealthService()

    with (
        patch.object(service, "_check_database", side_effect=Exception("db down")),
        patch.object(
            service,
            "_check_cache",
            return_value={"status": "healthy", "latency_ms": 1},
        ),
        patch.object(
            service,
            "_check_external_services",
            return_value={
                "status": "healthy",
                "services": {"aws_sts": {"status": "healthy"}},
            },
        ),
        patch.object(
            service,
            "_check_circuit_breakers",
            return_value={"status": "healthy"},
        ),
        patch.object(
            service,
            "_check_system_resources",
            return_value={"status": "healthy"},
        ),
        patch.object(
            service,
            "_check_background_jobs",
            side_effect=Exception("jobs down"),
        ),
    ):
        result = await service.comprehensive_health_check()

    assert result["status"] == "unhealthy"
    assert result["checks"]["database"]["status"] == "down"
    assert result["checks"]["database"]["error"] == "db down"
    assert result["checks"]["background_jobs"]["status"] == "unknown"
    assert result["checks"]["background_jobs"]["error"] == "jobs down"


@pytest.mark.asyncio
async def test_run_health_check_rejects_non_mapping_payload():
    service = HealthService()

    async def invalid_payload():
        return "not-a-dict"

    result = await service._run_health_check(
        invalid_payload(),
        component="cache",
    )

    assert result["status"] == "unhealthy"
    assert result["component"] == "cache"
    assert result["error"] == "Health check returned non-dict payload"
