from __future__ import annotations

from typing import Any
import ssl

import structlog


def build_connect_args(
    settings_obj: Any,
    effective_url: str,
    *,
    logger: Any | None = None,
) -> dict[str, Any]:
    connect_args: dict[str, Any] = {}
    ssl_mode = str(getattr(settings_obj, "DB_SSL_MODE", "require")).lower()
    target_logger = logger or structlog.get_logger()
    is_postgres = "postgresql" in effective_url
    environment = str(getattr(settings_obj, "ENVIRONMENT", "") or "").strip().lower()
    is_local_env = environment in {"local", "development"}

    if is_postgres:
        connect_args["statement_cache_size"] = 0  # Required for Supavisor

    if ssl_mode == "disable":
        if is_postgres:
            log_method = target_logger.debug if is_local_env else target_logger.warning
            log_method(
                "database_ssl_disabled",
                msg="SSL disabled - INSECURE, do not use in production!",
                environment=environment or "unknown",
            )
        else:
            target_logger.debug(
                "database_ssl_disable_ignored_non_postgres",
                environment=environment or "unknown",
                effective_url=effective_url,
            )
        if is_postgres:
            connect_args["ssl"] = False
        return connect_args

    if ssl_mode == "require":
        ssl_context = ssl.create_default_context()
        if getattr(settings_obj, "DB_SSL_CA_CERT_PATH", None):
            ssl_context.load_verify_locations(cafile=settings_obj.DB_SSL_CA_CERT_PATH)
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            ssl_context.check_hostname = True
            target_logger.info(
                "database_ssl_require_verified",
                ca_cert=settings_obj.DB_SSL_CA_CERT_PATH,
            )
        else:
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            ssl_context.check_hostname = True
            target_logger.info(
                "database_ssl_require_system_trust",
                msg=(
                    "SSL enabled with system trust store verification. "
                    "Set DB_SSL_CA_CERT_PATH to pin an explicit CA bundle."
                ),
            )
        if is_postgres:
            connect_args["ssl"] = ssl_context
        return connect_args

    if ssl_mode in {"verify-ca", "verify-full"}:
        ca_cert = getattr(settings_obj, "DB_SSL_CA_CERT_PATH", None)
        if not ca_cert:
            raise ValueError(f"DB_SSL_CA_CERT_PATH required for ssl_mode={ssl_mode}")
        ssl_context = ssl.create_default_context(cafile=ca_cert)
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = ssl_mode == "verify-full"
        if is_postgres:
            connect_args["ssl"] = ssl_context
        target_logger.info("database_ssl_verified", mode=ssl_mode, ca_cert=ca_cert)
        return connect_args

    raise ValueError(
        f"Invalid DB_SSL_MODE: {ssl_mode}. Use: disable, require, verify-ca, verify-full"
    )
