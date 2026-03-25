from __future__ import annotations

import asyncio
from typing import Any

from httpx import ASGITransport, AsyncClient, Response


class SyncASGIClient:
    def __init__(
        self,
        app: Any,
        *,
        base_url: str = "http://test",
        raise_app_exceptions: bool = True,
    ) -> None:
        self.app = app
        self.base_url = base_url
        self.raise_app_exceptions = raise_app_exceptions

    def request(self, method: str, *args: Any, **kwargs: Any) -> Response:
        async def _send() -> Response:
            transport = ASGITransport(
                app=self.app,
                raise_app_exceptions=self.raise_app_exceptions,
            )
            async with AsyncClient(
                transport=transport,
                base_url=self.base_url,
            ) as client:
                return await client.request(method, *args, **kwargs)

        return asyncio.run(_send())

    def get(self, *args: Any, **kwargs: Any) -> Response:
        return self.request("GET", *args, **kwargs)

    def post(self, *args: Any, **kwargs: Any) -> Response:
        return self.request("POST", *args, **kwargs)

    def put(self, *args: Any, **kwargs: Any) -> Response:
        return self.request("PUT", *args, **kwargs)

    def patch(self, *args: Any, **kwargs: Any) -> Response:
        return self.request("PATCH", *args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> Response:
        return self.request("DELETE", *args, **kwargs)

    def options(self, *args: Any, **kwargs: Any) -> Response:
        return self.request("OPTIONS", *args, **kwargs)

    def close(self) -> None:
        return None

    def __enter__(self) -> "SyncASGIClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
