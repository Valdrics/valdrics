from __future__ import annotations

import asyncio


class MetricStub:
    def __init__(self) -> None:
        self.inc_calls = 0
        self.set_calls = 0

    def labels(self, **_kwargs: object) -> "MetricStub":
        return self

    def set(self, _value: object) -> None:
        self.set_calls += 1

    def inc(self) -> None:
        self.inc_calls += 1


class DummyManager:
    _local_inflight_counts: dict[str, int] = {}
    _local_inflight_lock = asyncio.Lock()
