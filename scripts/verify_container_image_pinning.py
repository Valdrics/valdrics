"""Verify deterministic container image references in compose files."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Any, Mapping

import yaml
from dotenv import dotenv_values

DEFAULT_REPO_ROOT = Path(".")
DEFAULT_COMPOSE_PATHS: tuple[Path, ...] = (
    Path("docker-compose.yml"),
    Path("docker-compose.observability.yml"),
    Path("docker-compose.prod.yml"),
)
MUTABLE_TAGS = {"latest"}
SHA256_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
INTERPOLATION_RE = re.compile(r"\$\{([^}]+)\}")
VARIABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _resolve_path(*, repo_root: Path, compose_path: Path) -> Path:
    return compose_path if compose_path.is_absolute() else repo_root / compose_path


def _is_variable_ref(value: str) -> bool:
    return "${" in value and "}" in value


def _load_interpolation_environment(
    *, repo_root: Path, environment: Mapping[str, str] | None
) -> dict[str, str]:
    env_path = repo_root / ".env"
    resolved: dict[str, str] = {}
    if env_path.exists():
        resolved.update(
            {
                str(key): str(value)
                for key, value in dotenv_values(env_path).items()
                if value is not None
            }
        )
    source_environment = environment if environment is not None else os.environ
    resolved.update({str(key): str(value) for key, value in source_environment.items()})
    return resolved


def _resolve_interpolation_token(expression: str, environment: Mapping[str, str]) -> str:
    for operator in (":-", ":?", "?", "-"):
        if operator not in expression:
            continue
        variable_name, operand = expression.split(operator, 1)
        variable_name = variable_name.strip()
        if not VARIABLE_NAME_RE.fullmatch(variable_name):
            raise ValueError(f"unsupported interpolation token: {expression}")
        value = environment.get(variable_name)
        if operator == ":-":
            return value if value not in {None, ""} else operand
        if operator == "-":
            return value if value is not None else operand
        if operator == ":?":
            if value not in {None, ""}:
                return value
            raise ValueError(operand or f"{variable_name} must be set")
        if value is not None:
            return value
        raise ValueError(operand or f"{variable_name} must be set")

    variable_name = expression.strip()
    if not VARIABLE_NAME_RE.fullmatch(variable_name):
        raise ValueError(f"unsupported interpolation token: {expression}")
    if variable_name not in environment:
        raise ValueError(f"{variable_name} must be set")
    return environment[variable_name]


def _resolve_image_ref(image_ref: str, *, environment: Mapping[str, str]) -> str:
    def _replace(match: re.Match[str]) -> str:
        return _resolve_interpolation_token(match.group(1), environment)

    return INTERPOLATION_RE.sub(_replace, image_ref)


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
    environment: Mapping[str, str],
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
        try:
            image_ref = _resolve_image_ref(image_ref, environment=environment)
        except ValueError as exc:
            return (
                f"{compose_path.as_posix()}:{service_name} image reference could not be resolved: {exc}",
            )
        if not image_ref.strip():
            return (
                f"{compose_path.as_posix()}:{service_name} image reference resolved to an empty value",
            )

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
    environment: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    errors: list[str] = []
    interpolation_environment = _load_interpolation_environment(
        repo_root=repo_root,
        environment=environment,
    )

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
                    environment=interpolation_environment,
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
