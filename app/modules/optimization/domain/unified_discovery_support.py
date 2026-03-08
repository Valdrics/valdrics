from __future__ import annotations

AWS_NATIVE_DISCOVERY_RECOVERABLE_EXCEPTIONS = (
    RuntimeError,
    OSError,
    TimeoutError,
    TypeError,
    ValueError,
    KeyError,
    AttributeError,
)


def tags_to_dict(raw_tags: object) -> dict[str, str]:
    if not isinstance(raw_tags, list):
        return {}
    tags: dict[str, str] = {}
    for entry in raw_tags:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("Key") or "").strip()
        value = str(entry.get("Value") or "").strip()
        if key:
            tags[key] = value
    return tags


def build_arn(
    *,
    service: str,
    region: str,
    account_id: str,
    resource_segment: str,
    resource_id: str,
) -> str:
    return f"arn:aws:{service}:{region}:{account_id}:{resource_segment}/{resource_id}"
