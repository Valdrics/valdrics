from __future__ import annotations

from typing import Any


def build_migration_context_kwargs(
    *,
    connection: Any,
    target_metadata: Any,
    include_object: Any,
    compare_type: Any,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "connection": connection,
        "target_metadata": target_metadata,
        "include_object": include_object,
        "compare_type": compare_type,
    }
    if str(getattr(getattr(connection, "dialect", None), "name", "")).lower() == "sqlite":
        kwargs["render_as_batch"] = True
    return kwargs
