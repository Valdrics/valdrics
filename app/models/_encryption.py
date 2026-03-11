"""
Centralized encryption key resolver for ORM column definitions.

StringEncryptedType accepts a callable for the `key` parameter, which is
evaluated at encrypt/decrypt time rather than at import time. This decouples
model imports from the ENCRYPTION_KEY environment variable, enabling:

- Tests to import models without requiring ENCRYPTION_KEY
- Tooling and scripts to introspect models without full environment setup
- Fail-fast at first actual encryption operation, not at import
- Runtime key rotation via settings reload without a process restart

Usage in models:
    from app.models._encryption import get_encryption_key
    ...
    name: Mapped[str] = mapped_column(
        StringEncryptedType(String, get_encryption_key, AesEngine, "pkcs5")
    )
"""


def get_encryption_key() -> str:
    """
    Lazily resolve the encryption key from settings.

    We intentionally do not keep a second module-level raw key cache here.
    ``get_settings()`` is already cached centrally, and avoiding a duplicate raw
    key cache keeps ORM encryption aligned with runtime settings reloads and key
    rotation behavior.
    """
    from app.shared.core.config import get_settings

    settings = get_settings()
    key = settings.ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY not set. Cannot perform encryption operations. "
            "Set the ENCRYPTION_KEY environment variable before accessing encrypted data."
        )
    return key


def clear_encryption_key_cache() -> None:
    """
    Compatibility hook for config reload and tests.

    ORM encryption now resolves directly against the cached settings object, so
    there is no longer a second module-level raw key cache to clear here.
    """
    return None
