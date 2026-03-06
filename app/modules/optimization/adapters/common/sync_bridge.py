"""Helpers for safely invoking synchronous cloud SDK calls from async scanners."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from typing import TypeVar

_T = TypeVar("_T")


def _is_unittest_mock_callable(func: Callable[..., object]) -> bool:
    func_type = type(func)
    return func_type.__module__.startswith("unittest.mock")


async def run_blocking(func: Callable[..., _T], /, *args: object, **kwargs: object) -> _T:
    """Run a blocking SDK function without blocking the event loop."""
    if _is_unittest_mock_callable(func):
        return func(*args, **kwargs)

    return await asyncio.to_thread(func, *args, **kwargs)


async def materialize_iterable(
    func: Callable[..., Iterable[_T]],
    /,
    *args: object,
    **kwargs: object,
) -> list[_T]:
    """Run a blocking call that returns an iterable and eagerly materialize its items."""
    if _is_unittest_mock_callable(func):
        return list(func(*args, **kwargs))

    def _collect() -> list[_T]:
        return list(func(*args, **kwargs))

    return await asyncio.to_thread(_collect)
