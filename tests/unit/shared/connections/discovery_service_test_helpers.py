from __future__ import annotations

import httpx


class _FakeScalars:
    def __init__(self, values: list[object]):
        self._values = list(values)

    def all(self) -> list[object]:
        return list(self._values)

    def first(self) -> object | None:
        return self._values[0] if self._values else None


class _FakeResult:
    def __init__(self, *, one: object | None = None, values: list[object] | None = None):
        self._one = one
        self._values = list(values or [])

    def scalar_one_or_none(self) -> object | None:
        return self._one

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._values)


class _FakeDB:
    def __init__(self, results: list[_FakeResult]):
        self._results = list(results)
        self.added: list[object] = []
        self.commits = 0
        self.refreshed: list[object] = []

    async def execute(self, _stmt: object) -> _FakeResult:
        if not self._results:
            raise AssertionError("No fake DB result configured for execute")
        return self._results.pop(0)

    def add(self, item: object) -> None:
        self.added.append(item)

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, item: object) -> None:
        self.refreshed.append(item)


class _FakeHttpClient:
    def __init__(self, responses: list[object]):
        self.responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    async def request(self, method: str, url: str, headers: dict[str, str]) -> httpx.Response:
        self.calls.append((method, url))
        if not self.responses:
            raise AssertionError("No fake response configured for HTTP request")
        next_item = self.responses.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item


def _json_response(status_code: int, payload: object) -> httpx.Response:
    request = httpx.Request("GET", "https://example.invalid")
    return httpx.Response(status_code, request=request, json=payload)


class _MXRecord:
    def __init__(self, exchange: str):
        self.exchange = exchange


class _BrokenMXRecord:
    @property
    def exchange(self) -> str:
        raise RuntimeError("bad record")


class _CNAMERecord:
    def __init__(self, target: str):
        self.target = target


class _TXTRecord:
    def __init__(self, text: str):
        self._text = text

    def to_text(self) -> str:
        return self._text

