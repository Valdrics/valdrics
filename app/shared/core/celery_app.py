from celery import Celery
from app.shared.core.config import get_settings
from app.shared.core.runtime_dependencies import validate_runtime_dependencies

settings = get_settings()

CELERY_TASK_MODULES = ["app.tasks.scheduler_tasks", "app.tasks.license_tasks"]


def _redis_broker_url(settings_obj=None) -> str:
    settings_obj = settings_obj or get_settings()
    configured_url = str(getattr(settings_obj, "REDIS_URL", "") or "").strip()
    if configured_url:
        return configured_url

    host = str(getattr(settings_obj, "REDIS_HOST", "") or "").strip()
    port = str(getattr(settings_obj, "REDIS_PORT", "") or "").strip()
    if host and port:
        return f"redis://{host}:{port}/0"

    if settings_obj.TESTING:
        return "memory://"

    if getattr(settings_obj, "is_strict_environment", False):
        raise RuntimeError(
            "REDIS_URL is required for worker startup in staging/production."
        )

    return "redis://localhost:6379/0"


# Initialize Celery app
celery_app = Celery(
    "valdrics_worker",
    include=CELERY_TASK_MODULES,
)

def refresh_celery_app_config(settings_obj=None) -> None:
    settings_obj = settings_obj or get_settings()
    if not settings_obj.TESTING:
        validate_runtime_dependencies(settings_obj)

    broker_url = _redis_broker_url(settings_obj)
    backend_url = broker_url
    celery_app.conf.update(
        broker_url=broker_url,
        result_backend=backend_url,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        include=CELERY_TASK_MODULES,
        # Worker settings
        worker_prefetch_multiplier=1,  # Prevent worker from hogging tasks (fair dispatch)
        task_acks_late=True,  # Retry if worker crashes mid-task
        task_reject_on_worker_lost=True,
        # Connection settings - CRITICAL: prevents indefinite blocking during startup
        broker_connection_timeout=5,  # 5 second timeout for broker connection
        broker_connection_retry=True,  # Enable retries
        broker_connection_max_retries=3,  # Max 3 retries
        broker_connection_retry_on_startup=True,  # Retry briefly on startup instead of failing immediately
        task_always_eager=False,
        task_eager_propagates=False,
    )

    # BE-TEST-2: Support eager execution for unit tests without Redis
    if settings_obj.TESTING:
        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
            broker_url="memory://",
            result_backend="rpc://",
            broker_connection_retry_on_startup=False,  # Never block in tests
        )


refresh_celery_app_config(settings)

if __name__ == "__main__":
    celery_app.start()
