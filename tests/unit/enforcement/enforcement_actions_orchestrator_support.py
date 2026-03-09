from __future__ import annotations

from unittest.mock import AsyncMock


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _ScalarsResult:
    def __init__(self, values) -> None:  # type: ignore[no-untyped-def]
        self._values = list(values)

    def all(self):  # type: ignore[no-untyped-def]
        return list(self._values)


class _RowsResult:
    def __init__(self, values) -> None:  # type: ignore[no-untyped-def]
        self._values = list(values)

    def scalars(self) -> _ScalarsResult:
        return _ScalarsResult(self._values)


class _RowCountResult:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class _QueueDB:
    def __init__(self, execute_results: list[object]) -> None:
        self._execute_results = list(execute_results)
        self.rollback = AsyncMock()
        self.commit = AsyncMock()
        self.refresh = AsyncMock()
        self.added: list[object] = []

    async def execute(self, *_args, **_kwargs) -> object:
        if not self._execute_results:
            raise AssertionError("No queued execute result available")
        return self._execute_results.pop(0)

    def add(self, value: object) -> None:
        self.added.append(value)
