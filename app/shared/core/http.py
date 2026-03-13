"""
Async HTTP Client Shared Infrastructure (2026 Standards)

Ensures singleton httpx.AsyncClient usage across both FastAPI lifespan
and background workers to prevent socket exhaustion and optimize latency.
"""

import asyncio
from collections.abc import Awaitable, Coroutine
import inspect
from typing import Optional
import httpx
import structlog

from app.shared.core.outbound_tls import resolve_outbound_tls_verification

logger = structlog.get_logger()

# Singleton instances
_client: Optional[httpx.AsyncClient] = None
_insecure_client: Optional[httpx.AsyncClient] = None


def _current_loop_marker() -> int | None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return None
    if loop.is_closed():
        return None
    return id(loop)


def _build_http_client(
    *,
    verify: bool,
    timeout: Optional[float],
    limits: httpx.Limits | None = None,
    user_agent: str | None = None,
) -> httpx.AsyncClient:
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(timeout or 20.0, connect=10.0),
        limits=limits or httpx.Limits(max_connections=100, max_keepalive_connections=20),
        http2=True,
        verify=verify,
        headers={"User-Agent": user_agent} if user_agent else None,
    )
    setattr(client, "_valdrics_loop_marker", _current_loop_marker())
    return client


def _schedule_client_close(client: httpx.AsyncClient) -> None:
    aclose = getattr(client, "aclose", None)
    if not callable(aclose):
        return

    close_result = aclose()
    if inspect.isawaitable(close_result):
        close_awaitable = close_result
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            close = getattr(close_awaitable, "close", None)
            if callable(close):
                close()
            return
        if isinstance(close_awaitable, Coroutine):
            loop.create_task(close_awaitable)
            return

        async def _await_close_result(result: Awaitable[object]) -> None:
            await result

        loop.create_task(_await_close_result(close_awaitable))


def _client_needs_reinitialization(client: httpx.AsyncClient) -> bool:
    if getattr(client, "is_closed", False):
        return True

    current_loop_marker = _current_loop_marker()
    client_loop_marker = getattr(client, "_valdrics_loop_marker", None)
    return bool(
        current_loop_marker is not None
        and client_loop_marker is not None
        and current_loop_marker != client_loop_marker
    )


def get_http_client(
    verify: bool = True, timeout: Optional[float] = None
) -> httpx.AsyncClient:
    """
    Returns a global shared httpx.AsyncClient.
    Maintains separate pools for secure and explicitly authorized insecure connections.
    """
    global _client, _insecure_client
    verify = resolve_outbound_tls_verification(verify)

    target = _client if verify else _insecure_client

    if target is not None and _client_needs_reinitialization(target):
        logger.warning(
            "http_client_reinitialized",
            verify=verify,
            reason="closed_or_event_loop_changed",
        )
        _schedule_client_close(target)
        if verify:
            _client = None
        else:
            _insecure_client = None
        target = None

    if target is None:
        logger.warning(
            "http_client_lazy_initialized",
            verify=verify,
            msg="Client was not pre-initialized",
        )
        new_client = _build_http_client(verify=verify, timeout=timeout)
        if verify:
            _client = new_client
        else:
            _insecure_client = new_client
        return new_client

    return target


async def init_http_client() -> None:
    """
    Initializes the global httpx.AsyncClient with 2026 production settings.
    """
    global _client
    if _client is not None:
        logger.warning("http_client_already_initialized")
        return

    _client = _build_http_client(
        verify=True,
        timeout=20.0,
        limits=httpx.Limits(
            max_connections=500,
            max_keepalive_connections=50,
            keepalive_expiry=30.0,
        ),
        user_agent="Valdrics-AI/2026.02",
    )
    logger.info("http_client_initialized", http2=True, max_connections=500)


async def close_http_client() -> None:
    """
    Gracefully shuts down the global client, flushing all connection pools.
    """
    global _client, _insecure_client

    async def _close_one(client: object | None, label: str) -> None:
        if not client:
            return

        close_result = None
        aclose = getattr(client, "aclose", None)
        if callable(aclose):
            close_result = aclose()
        else:
            close = getattr(client, "close", None)
            if callable(close):
                close_result = close()

        if inspect.isawaitable(close_result):
            await close_result

        logger.info("http_client_closed", verify=label == "secure")

    await _close_one(_client, "secure")
    await _close_one(_insecure_client, "insecure")
    _client = None
    _insecure_client = None
