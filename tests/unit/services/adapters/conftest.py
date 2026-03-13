from __future__ import annotations

import pytest

from app.shared.core import http as http_module


@pytest.fixture(autouse=True)
def reset_shared_http_client_singletons() -> None:
    http_module._client = None
    http_module._insecure_client = None
    yield
    http_module._client = None
    http_module._insecure_client = None
