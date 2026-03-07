"""Verify deterministic container image references in compose files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import yaml

DEFAULT_REPO_ROOT = Path(".")
DEFAULT_COMPOSE_PATHS: tuple[Path, ...] = (
    Path("docker-compose.yml"),
    Path("docker-compose.observability.yml"),
    Path("docker-compose.prod.yml"),
)
MUTABLE_TAGS = {"latest"}
SHA256_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def _resolve_path(*, repo_root: Path, compose_path: Path) -> Path:
    return compose_path if compose_path.is_absolute() else repo_root / compose_path


def _is_variable_ref(value: str) -> bool:
    return "${" in value and "}" in value


def _extract_tag(image_ref: str) -> str | None:
    # `registry:5000/name:tag` should resolve to `tag` while preserving registry port.
    last_slash = image_ref.rfind("/")
    last_colon = image_ref.rfind(":")
    if last_colon <= last_slash:
        return None
    return image_ref[last_colon + 1 :].strip() or None


def _service_has_build(service_def: dict[str, Any]) -> bool:
    return "build" in service_def


def _verify_service_image(
    *,
    compose_path: Path,
    service_name: str,
    service_def: dict[str, Any],
) -> tuple[str, ...]:
    image_value = service_def.get("image")
    if image_value is None:
        return ()

    image_ref = str(image_value).strip()
    if not image_ref:
        return (
            f"{compose_path.as_posix()}:{service_name} image reference must not be empty",
        )
    if _is_variable_ref(image_ref):
        return ()

    if "@sha256:" in image_ref:
        digest = image_ref.split("@sha256:", 1)[1].strip()
        if SHA256_DIGEST_RE.fullmatch(digest):
            return ()
        return (
            f"{compose_path.as_posix()}:{service_name} image digest must be sha256:<64-hex>: {image_ref}",
        )

    tag = _extract_tag(image_ref)
    if tag is None:
        if _service_has_build(service_def):
            return ()
        return (
            f"{compose_path.as_posix()}:{service_name} image must include an immutable tag or digest: {image_ref}",
        )

    if tag.lower() in MUTABLE_TAGS:
        return (
            f"{compose_path.as_posix()}:{service_name} image uses mutable tag '{tag}': {image_ref}",
        )
    return ()


def _load_compose_services(path: Path) -> tuple[dict[str, Any], tuple[str, ...]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload is None:
        return {}, ()
    if not isinstance(payload, dict):
        return {}, (f"{path.as_posix()} must contain a top-level mapping",)
    services = payload.get("services", {})
    if not isinstance(services, dict):
        return {}, (f"{path.as_posix()} has invalid 'services' mapping",)
    return services, ()


def verify_container_image_pinning(
    *,
    repo_root: Path,
    compose_paths: tuple[Path, ...] = DEFAULT_COMPOSE_PATHS,
) -> tuple[str, ...]:
    errors: list[str] = []

    for compose_path in compose_paths:
        resolved = _resolve_path(repo_root=repo_root, compose_path=compose_path)
        if not resolved.exists():
            errors.append(f"missing compose file: {resolved.as_posix()}")
            continue
        services, parse_errors = _load_compose_services(resolved)
        errors.extend(parse_errors)
        if parse_errors:
            continue
        for service_name, service_def in services.items():
            if not isinstance(service_def, dict):
                errors.append(
                    f"{resolved.as_posix()}:{service_name} service definition must be a mapping"
                )
                continue
            errors.extend(
                _verify_service_image(
                    compose_path=resolved,
                    service_name=str(service_name),
                    service_def=service_def,
                )
            )
    return tuple(errors)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify compose image references are deterministic and non-mutable."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Repository root path.",
    )
    parser.add_argument(
        "--compose-path",
        action="append",
        type=Path,
        default=[],
        help=(
            "Compose file path to validate (relative to repo root by default). "
            "Can be repeated."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    compose_paths = tuple(args.compose_path) or DEFAULT_COMPOSE_PATHS
    errors = verify_container_image_pinning(
        repo_root=repo_root,
        compose_paths=compose_paths,
    )
    if errors:
        print("[container-image-pinning] FAILED")
        for item in errors:
            print(f"- {item}")
        return 1
    print(
        "[container-image-pinning] ok "
        f"repo_root={repo_root.as_posix()} files={len(compose_paths)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
