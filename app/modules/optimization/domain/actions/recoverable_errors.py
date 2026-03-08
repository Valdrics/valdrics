from __future__ import annotations


def remediation_action_recoverable_exceptions() -> tuple[type[Exception], ...]:
    base_exceptions: list[type[Exception]] = [
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        LookupError,
    ]
    try:
        from botocore.exceptions import ClientError
    except ImportError:
        pass
    else:
        base_exceptions.insert(0, ClientError)
    return tuple(base_exceptions)
