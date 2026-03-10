"""Shared helpers for rendering and parsing shell-source-safe env files."""

from __future__ import annotations

from pathlib import Path
import shlex


def render_env_value(value: str) -> str:
    if value == "":
        return ""
    return shlex.quote(value)


def render_env(template_lines: list[str], overrides: dict[str, str]) -> str:
    output_lines: list[str] = []
    seen: set[str] = set()
    for raw_line in template_lines:
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            output_lines.append(line)
            continue

        key, _, value = line.partition("=")
        normalized_key = key.strip()
        if normalized_key in overrides:
            output_lines.append(
                f"{normalized_key}={render_env_value(overrides[normalized_key])}"
            )
            seen.add(normalized_key)
            continue

        output_lines.append(f"{normalized_key}={render_env_value(value)}")

    for key in sorted(candidate for candidate in overrides if candidate not in seen):
        output_lines.append(f"{key}={render_env_value(overrides[key])}")

    output_lines.append("")
    return "\n".join(output_lines)


def parse_env_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in str(text or "").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw_line:
            continue
        key, _, value = raw_line.partition("=")
        rendered_value = value.strip()
        if rendered_value == "":
            values[key.strip()] = ""
            continue
        if rendered_value.startswith(("[", "{")):
            values[key.strip()] = rendered_value
            continue
        parsed = shlex.split(rendered_value, posix=True)
        values[key.strip()] = parsed[0] if parsed else ""
    return values


def parse_env_file(path: Path) -> dict[str, str]:
    return parse_env_text(path.read_text(encoding="utf-8"))
