"""Shared deterministic derivation helpers for local-only env generators."""

from __future__ import annotations

import base64
import hashlib


def derive_digest(seed: str, key: str) -> bytes:
    return hashlib.sha256(f"{seed}:{key}".encode("utf-8")).digest()


def derive_hex(seed: str, key: str, *, length: int = 64) -> str:
    material = hashlib.sha512(f"{seed}:{key}".encode("utf-8")).hexdigest()
    while len(material) < length:
        material += hashlib.sha512(material.encode("utf-8")).hexdigest()
    return material[:length]


def derive_urlsafe_b64(seed: str, key: str) -> str:
    return base64.urlsafe_b64encode(derive_digest(seed, key)).decode("utf-8")


def derive_b64(seed: str, key: str) -> str:
    return base64.b64encode(derive_digest(seed, key)).decode("utf-8")
