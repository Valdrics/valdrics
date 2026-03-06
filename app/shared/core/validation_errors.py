"""Validation error sanitization helpers."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence


def json_safe(value: Any) -> Any:
    if isinstance(value, Exception):
        return str(value)
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def sanitize_validation_errors(errors: Sequence[Any]) -> List[Dict[str, Any]]:
    sanitized: List[Dict[str, Any]] = []
    for err in errors:
        clean = dict(err)
        if "ctx" in clean and isinstance(clean["ctx"], dict):
            clean["ctx"] = {k: json_safe(v) for k, v in clean["ctx"].items()}
        if "input" in clean:
            clean["input"] = json_safe(clean["input"])
        sanitized.append(clean)
    return sanitized
