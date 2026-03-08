from __future__ import annotations

from typing import Any


def get_adapter_for_connection(connection: Any) -> Any:
    """Resolve the runtime adapter for a stored connection via the shared adapter factory."""
    from app.shared.adapters.factory import AdapterFactory

    return AdapterFactory.get_adapter(connection)
