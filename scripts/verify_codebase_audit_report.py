#!/usr/bin/env python3
"""Verify checked-in codebase audit report JSON artifacts stay coherent."""

from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.env_generation_common import (
    repo_root_for,
    resolve_cli_path_from_root,
    resolve_contained_repo_path_from_root,
)

DEFAULT_ROOT = repo_root_for(__file__)
DEFAULT_REPORT = Path(".runtime/staging.audit.report.json")
EXPECTED_ARTIFACT_TYPE = "codebase_audit_validation"
ALLOWED_VALIDATION_STATUSES = frozenset(
    {"accurate", "partially_accurate", "inaccurate"}
)
ALLOWED_PARTIAL_STATUSES = frozenset({"partial", "overstated"})
REQUIRED_STRING_FIELDS = (
    "artifact_type",
    "snapshot_date",
    "environment",
    "repository",
    "product_name",
    "source_report_label",
    "validation_status",
)
REQUIRED_LIST_FIELDS = ("validation_scope", "validation_commands", "limitations")
REQUIRED_MEASURED_STRING_FIELDS = (
    "python_requires",
    "fastapi_requirement",
    "frontend_svelte_version",
    "frontend_sveltekit_version",
)
REQUIRED_MEASURED_INTEGER_FIELDS = (
    "backend_tests_collected",
    "test_and_spec_files",
    "zombie_plugin_classes",
    "direct_audit_logger_call_sites",
)
CLAIM_SECTIONS = (
    "confirmed_claims",
    "partial_or_overstated_claims",
    "incorrect_claims",
)
VALIDATION_RUN_FINDING_SECTIONS = (
    "confirmed_findings",
    "watch_items",
    "incorrect_or_stale_findings",
    "remediations_applied",
)
TEST_AND_SPEC_GLOBS = (
    "tests/**/*.py",
    "dashboard/**/*.test.ts",
    "dashboard/**/*.test.js",
    "dashboard/**/*.test.tsx",
    "dashboard/**/*.test.jsx",
    "dashboard/**/*.test.svelte",
    "dashboard/**/*.spec.ts",
    "dashboard/**/*.spec.js",
    "dashboard/**/*.spec.tsx",
    "dashboard/**/*.spec.jsx",
    "dashboard/**/*.spec.svelte",
)
TEST_AND_SPEC_EXCLUDED_PARTS = frozenset(
    {"node_modules", ".svelte-kit", "dist", "coverage", "playwright-report"}
)
MEASURED_FACT_INTEGER_FIELDS = frozenset(REQUIRED_MEASURED_INTEGER_FIELDS)
MEASURED_FACT_STRING_FIELDS = frozenset(REQUIRED_MEASURED_STRING_FIELDS)


def _expect(condition: bool, message: str, *, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _label(path: Path, *, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path.as_posix()}")
    return payload


def _validate_non_empty_string(value: Any, *, label: str, errors: list[str]) -> None:
    _expect(
        isinstance(value, str) and bool(value.strip()),
        f"{label} must be a non-empty string",
        errors=errors,
    )


def _validate_string_list(
    value: Any,
    *,
    label: str,
    errors: list[str],
) -> None:
    if not isinstance(value, list) or not value:
        errors.append(f"{label} must be a non-empty list")
        return
    for index, item in enumerate(value):
        _validate_non_empty_string(
            item,
            label=f"{label}[{index}]",
            errors=errors,
        )


def _looks_like_repo_path(value: str) -> bool:
    return not any(character.isspace() for character in value)


def _validate_evidence_items(
    evidence: Any,
    *,
    root: Path,
    label: str,
    require_non_empty: bool,
    errors: list[str],
) -> None:
    if evidence is None:
        if require_non_empty:
            errors.append(f"{label}.evidence must be present")
        return

    if not isinstance(evidence, list):
        errors.append(f"{label}.evidence must be a list")
        return

    if require_non_empty and not evidence:
        errors.append(f"{label}.evidence must be a non-empty list")
        return

    for index, item in enumerate(evidence):
        item_label = f"{label}.evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_label} must be an object")
            continue

        path_value = item.get("path")
        _validate_non_empty_string(
            path_value,
            label=f"{item_label}.path",
            errors=errors,
        )

        if isinstance(path_value, str) and _looks_like_repo_path(path_value):
            try:
                resolved = resolve_contained_repo_path_from_root(
                    root,
                    path_value,
                    field_name=f"{item_label}.path",
                )
            except ValueError as exc:
                errors.append(str(exc))
            else:
                _expect(
                    resolved.exists(),
                    f"{item_label}.path must exist: {path_value}",
                    errors=errors,
                )

        line_value = item.get("line")
        if line_value is None:
            continue
        _expect(
            isinstance(line_value, int) and line_value >= 1,
            f"{item_label}.line must be a positive integer when present",
            errors=errors,
        )


def _validate_summary(summary: Any, *, errors: list[str]) -> None:
    if not isinstance(summary, dict):
        errors.append("summary must be an object")
        return

    _validate_non_empty_string(
        summary.get("overall"), label="summary.overall", errors=errors
    )
    _validate_string_list(
        summary.get("high_confidence_findings"),
        label="summary.high_confidence_findings",
        errors=errors,
    )
    _validate_string_list(
        summary.get("important_corrections"),
        label="summary.important_corrections",
        errors=errors,
    )


def _validate_measured_facts(measured_facts: Any, *, errors: list[str]) -> None:
    if not isinstance(measured_facts, dict):
        errors.append("measured_facts must be an object")
        return

    for field_name in REQUIRED_MEASURED_STRING_FIELDS:
        _validate_non_empty_string(
            measured_facts.get(field_name),
            label=f"measured_facts.{field_name}",
            errors=errors,
        )

    for field_name in REQUIRED_MEASURED_INTEGER_FIELDS:
        value = measured_facts.get(field_name)
        _expect(
            isinstance(value, int) and value >= 1,
            f"measured_facts.{field_name} must be a positive integer",
            errors=errors,
        )


def _load_pyproject_metadata(*, root: Path) -> dict[str, Any]:
    pyproject_path = root / "pyproject.toml"
    return tomllib.loads(pyproject_path.read_text(encoding="utf-8"))


def _load_dashboard_package_json(*, root: Path) -> dict[str, Any]:
    package_path = root / "dashboard" / "package.json"
    return json.loads(package_path.read_text(encoding="utf-8"))


def _extract_fastapi_requirement(pyproject_payload: dict[str, Any]) -> str:
    dependencies = (
        pyproject_payload.get("project", {}).get("dependencies", [])
        if isinstance(pyproject_payload.get("project"), dict)
        else []
    )
    for dependency in dependencies:
        if not isinstance(dependency, str):
            continue
        normalized = dependency.strip()
        if not normalized.startswith("fastapi"):
            continue
        return normalized.removeprefix("fastapi").strip()
    raise ValueError("could not determine fastapi_requirement from pyproject.toml")


def _package_version(
    package_payload: dict[str, Any], package_name: str, *, allow_dev: bool = False
) -> str:
    dependencies = package_payload.get("dependencies")
    if isinstance(dependencies, dict):
        value = dependencies.get(package_name)
        if isinstance(value, str) and value.strip():
            return value
    if allow_dev:
        dev_dependencies = package_payload.get("devDependencies")
        if isinstance(dev_dependencies, dict):
            value = dev_dependencies.get(package_name)
            if isinstance(value, str) and value.strip():
                return value
    raise ValueError(
        f"could not determine version for {package_name} from dashboard/package.json"
    )


def _has_dashboard_dependency(
    package_payload: dict[str, Any], package_name: str
) -> bool:
    for section_name in ("dependencies", "devDependencies"):
        section = package_payload.get(section_name)
        if isinstance(section, dict) and package_name in section:
            return True
    return False


def _derive_frontend_stack_phrase(*, root: Path) -> str:
    package_payload = _load_dashboard_package_json(root=root)
    stack = [
        "SvelteKit",
        "Svelte 5",
        "TypeScript",
        "Tailwind CSS v4",
        "Vitest",
        "Playwright",
    ]
    if _has_dashboard_dependency(package_payload, "chart.js"):
        stack.append("Chart.js")
    if len(stack) == 1:
        return stack[0]
    return ", ".join(stack[:-1]) + f", and {stack[-1]}"


def collect_live_measured_facts(*, root: Path) -> dict[str, Any]:
    pyproject_payload = _load_pyproject_metadata(root=root)
    package_payload = _load_dashboard_package_json(root=root)
    return {
        "python_requires": str(
            pyproject_payload.get("project", {}).get("requires-python", "")
        ).strip(),
        "fastapi_requirement": _extract_fastapi_requirement(pyproject_payload),
        "frontend_svelte_version": _package_version(package_payload, "svelte"),
        "frontend_sveltekit_version": _package_version(
            package_payload, "@sveltejs/kit"
        ),
        "backend_tests_collected": _collect_backend_tests_count(root=root),
        "test_and_spec_files": _count_test_and_spec_files(root=root),
        "zombie_plugin_classes": _count_zombie_plugin_classes(root=root),
        "direct_audit_logger_call_sites": _count_direct_audit_logger_call_sites(
            root=root
        ),
    }


def _collect_backend_tests_count(*, root: Path) -> int:
    env = {
        **os.environ,
        "DEBUG": "false",
        "UV_CACHE_DIR": os.environ.get(
            "UV_CACHE_DIR", str(Path(tempfile.gettempdir()) / "uv-cache")
        ),
    }
    commands: list[list[str]] = []
    if shutil.which("uv"):
        commands.append(["uv", "run", "pytest", "--collect-only", "-q"])
    commands.append([sys.executable, "-m", "pytest", "--collect-only", "-q"])

    failures: list[str] = []
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        output = "\n".join(
            chunk
            for chunk in (completed.stdout.strip(), completed.stderr.strip())
            if chunk
        )
        match = re.search(r"(\d+)\s+tests\s+collected", output)
        if completed.returncode == 0 and match is not None:
            return int(match.group(1))
        failures.append(f"{' '.join(command)} exited {completed.returncode}")

    raise ValueError(
        "could not determine backend_tests_collected from pytest collection output: "
        + "; ".join(failures)
    )


def _count_test_and_spec_files(*, root: Path) -> int:
    files: set[Path] = set()
    for pattern in TEST_AND_SPEC_GLOBS:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            if TEST_AND_SPEC_EXCLUDED_PARTS.intersection(path.parts):
                continue
            files.add(path)
    return len(files)


def _count_zombie_plugin_classes(*, root: Path) -> int:
    import ast

    count = 0
    adapters_root = root / "app/modules/optimization/adapters"
    for path in adapters_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for base in node.bases:
                base_name: str | None = None
                if isinstance(base, ast.Name):
                    base_name = base.id
                elif isinstance(base, ast.Attribute):
                    base_name = base.attr
                if base_name in {"ZombiePlugin", "BaseZombiePlugin"}:
                    count += 1
                    break
    return count


def _count_direct_audit_logger_call_sites(*, root: Path) -> int:
    import ast

    count = 0
    app_root = root / "app"
    excluded_path = "app/modules/governance/domain/security/audit_log.py"
    for path in app_root.rglob("*.py"):
        if path.as_posix().endswith(excluded_path):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func_name: str | None = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            if func_name in {"AuditLogger", "SystemAuditLogger"}:
                count += 1
    return count


def _validate_live_measured_facts(
    measured_facts: Any,
    *,
    root: Path,
    errors: list[str],
) -> None:
    if not isinstance(measured_facts, dict):
        return

    try:
        live_facts = collect_live_measured_facts(root=root)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        errors.append(f"live measured facts verification failed: {exc}")
        return

    for field_name in MEASURED_FACT_STRING_FIELDS | MEASURED_FACT_INTEGER_FIELDS:
        recorded_value = measured_facts.get(field_name)
        live_value = live_facts[field_name]
        _expect(
            recorded_value == live_value,
            (
                f"measured_facts.{field_name} must match live repo fact: "
                f"recorded={recorded_value!r} live={live_value!r}"
            ),
            errors=errors,
        )


def _validate_claim_consistency(
    payload: dict[str, Any],
    *,
    root: Path,
    errors: list[str],
) -> None:
    measured_facts = payload.get("measured_facts")
    if not isinstance(measured_facts, dict):
        return

    backend_tests_collected = measured_facts.get("backend_tests_collected")
    zombie_plugin_classes = measured_facts.get("zombie_plugin_classes")
    if not isinstance(backend_tests_collected, int) or not isinstance(
        zombie_plugin_classes, int
    ):
        return

    try:
        frontend_stack_phrase = _derive_frontend_stack_phrase(root=root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"frontend stack claim verification failed: {exc}")
        frontend_stack_phrase = None

    summary = payload.get("summary")
    if isinstance(summary, dict):
        important_corrections = summary.get("important_corrections")
        if isinstance(important_corrections, list):
            backend_phrase = f"Backend tests collected currently total {backend_tests_collected}, not 5358."
            zombie_phrase = f"Zombie detection plugin classes total {zombie_plugin_classes} across providers, not 11."
            _expect(
                backend_phrase in important_corrections,
                "summary.important_corrections must include the live backend test count correction",
                errors=errors,
            )
            _expect(
                zombie_phrase in important_corrections,
                "summary.important_corrections must include the live zombie plugin correction",
                errors=errors,
            )
        high_confidence_findings = summary.get("high_confidence_findings")
        if isinstance(high_confidence_findings, list) and frontend_stack_phrase:
            frontend_summary_phrase = f"The dashboard uses {frontend_stack_phrase}."
            _expect(
                frontend_summary_phrase in high_confidence_findings,
                "summary.high_confidence_findings must include the live frontend stack summary",
                errors=errors,
            )

    incorrect_claims = payload.get("incorrect_claims")
    if not isinstance(incorrect_claims, list):
        incorrect_claims = []

    confirmed_claims = payload.get("confirmed_claims")
    if isinstance(confirmed_claims, list) and frontend_stack_phrase:
        expected_frontend_claim = f"Frontend stack includes {frontend_stack_phrase}."
        confirmed_frontend_claims = [
            claim.get("claim") for claim in confirmed_claims if isinstance(claim, dict)
        ]
        _expect(
            expected_frontend_claim in confirmed_frontend_claims,
            "confirmed_claims must include the live frontend stack claim",
            errors=errors,
        )

    for claim in incorrect_claims:
        if not isinstance(claim, dict):
            continue
        claim_text = claim.get("claim")
        correction = claim.get("correction")
        evidence = claim.get("evidence")

        if claim_text == "Testing has 5,358 tests":
            _expect(
                isinstance(correction, str)
                and str(backend_tests_collected) in correction,
                "incorrect_claims testing correction must include the live backend test count",
                errors=errors,
            )
            evidence_line = None
            if (
                isinstance(evidence, list)
                and evidence
                and isinstance(evidence[0], dict)
            ):
                evidence_line = evidence[0].get("line")
            _expect(
                evidence_line == backend_tests_collected,
                "incorrect_claims testing evidence line must match the live backend test count",
                errors=errors,
            )

        if claim_text == "FinOps capabilities include 11 zombie detection plugins":
            _expect(
                isinstance(correction, str)
                and str(zombie_plugin_classes) in correction,
                "incorrect_claims zombie plugin correction must include the live plugin count",
                errors=errors,
            )


def _validate_claim_sections(
    payload: dict[str, Any],
    *,
    root: Path,
    errors: list[str],
) -> None:
    for section_name in CLAIM_SECTIONS:
        section = payload.get(section_name)
        if not isinstance(section, list) or not section:
            errors.append(f"{section_name} must be a non-empty list")
            continue

        for index, claim in enumerate(section):
            label = f"{section_name}[{index}]"
            if not isinstance(claim, dict):
                errors.append(f"{label} must be an object")
                continue

            _validate_non_empty_string(
                claim.get("claim"),
                label=f"{label}.claim",
                errors=errors,
            )

            require_evidence = section_name != "partial_or_overstated_claims"
            if section_name == "partial_or_overstated_claims":
                status = claim.get("status")
                _expect(
                    status in ALLOWED_PARTIAL_STATUSES,
                    (
                        f"{label}.status must be one of: "
                        + ", ".join(sorted(ALLOWED_PARTIAL_STATUSES))
                    ),
                    errors=errors,
                )
                require_evidence = status == "partial"

            if section_name != "confirmed_claims":
                _validate_non_empty_string(
                    claim.get("correction"),
                    label=f"{label}.correction",
                    errors=errors,
                )

            _validate_evidence_items(
                claim.get("evidence"),
                root=root,
                label=label,
                require_non_empty=require_evidence,
                errors=errors,
            )


def _validate_validation_runs(
    validation_runs: Any,
    *,
    root: Path,
    errors: list[str],
) -> None:
    if validation_runs is None:
        return

    if not isinstance(validation_runs, list) or not validation_runs:
        errors.append("validation_runs must be a non-empty list when present")
        return

    for run_index, run in enumerate(validation_runs):
        run_label = f"validation_runs[{run_index}]"
        if not isinstance(run, dict):
            errors.append(f"{run_label} must be an object")
            continue

        _validate_non_empty_string(
            run.get("report_label"),
            label=f"{run_label}.report_label",
            errors=errors,
        )
        _validate_non_empty_string(
            run.get("snapshot_date"),
            label=f"{run_label}.snapshot_date",
            errors=errors,
        )
        snapshot_date = run.get("snapshot_date")
        if isinstance(snapshot_date, str) and snapshot_date.strip():
            try:
                date.fromisoformat(snapshot_date)
            except ValueError:
                errors.append(
                    f"{run_label}.snapshot_date must be an ISO-8601 date (YYYY-MM-DD)"
                )

        validation_status = run.get("validation_status")
        _expect(
            validation_status in ALLOWED_VALIDATION_STATUSES,
            (
                f"{run_label}.validation_status must be one of: "
                + ", ".join(sorted(ALLOWED_VALIDATION_STATUSES))
            ),
            errors=errors,
        )
        _validate_non_empty_string(
            run.get("overall"),
            label=f"{run_label}.overall",
            errors=errors,
        )

        for section_name in VALIDATION_RUN_FINDING_SECTIONS:
            findings = run.get(section_name)
            section_label = f"{run_label}.{section_name}"
            if not isinstance(findings, list):
                errors.append(f"{section_label} must be a list")
                continue

            for finding_index, finding in enumerate(findings):
                finding_label = f"{section_label}[{finding_index}]"
                if not isinstance(finding, dict):
                    errors.append(f"{finding_label} must be an object")
                    continue

                _validate_non_empty_string(
                    finding.get("finding"),
                    label=f"{finding_label}.finding",
                    errors=errors,
                )
                _validate_evidence_items(
                    finding.get("evidence"),
                    root=root,
                    label=finding_label,
                    require_non_empty=True,
                    errors=errors,
                )


def _validate_deployment_notes(
    deployment_notes: Any,
    *,
    environment: str,
    errors: list[str],
) -> None:
    if not isinstance(deployment_notes, dict):
        errors.append("deployment_notes must be an object")
        return

    _expect(
        deployment_notes.get("env_report_left_untouched") is True,
        "deployment_notes.env_report_left_untouched must be true",
        errors=errors,
    )
    reason = deployment_notes.get("reason")
    _validate_non_empty_string(reason, label="deployment_notes.reason", errors=errors)
    if isinstance(reason, str):
        reserved_report = f".runtime/{environment}.report.json"
        _expect(
            reserved_report in reason,
            (
                "deployment_notes.reason must explain why the reserved managed "
                f"runtime report remains untouched: {reserved_report}"
            ),
            errors=errors,
        )


def verify_audit_report(
    *,
    root: Path,
    report_path: Path,
    enforce_live_measured_facts: bool = False,
) -> list[str]:
    if not root.exists():
        return [f"root not found: {root}"]
    if not root.is_dir():
        return [f"root must be a directory: {root}"]
    if not report_path.exists():
        return [f"report not found: {report_path}"]
    if not report_path.is_file():
        return [f"report must be a file: {report_path}"]

    try:
        payload = _load_json(report_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"{_label(report_path, root=root)}: {exc}"]

    errors: list[str] = []

    for field_name in REQUIRED_STRING_FIELDS:
        _validate_non_empty_string(
            payload.get(field_name),
            label=field_name,
            errors=errors,
        )

    artifact_type = payload.get("artifact_type")
    if isinstance(artifact_type, str):
        _expect(
            artifact_type == EXPECTED_ARTIFACT_TYPE,
            (
                "artifact_type must be "
                f"{EXPECTED_ARTIFACT_TYPE!r}, got {artifact_type!r}"
            ),
            errors=errors,
        )

    snapshot_date = payload.get("snapshot_date")
    if isinstance(snapshot_date, str) and snapshot_date.strip():
        try:
            date.fromisoformat(snapshot_date)
        except ValueError:
            errors.append("snapshot_date must be an ISO-8601 date (YYYY-MM-DD)")

    validation_status = payload.get("validation_status")
    if isinstance(validation_status, str):
        _expect(
            validation_status in ALLOWED_VALIDATION_STATUSES,
            (
                "validation_status must be one of: "
                + ", ".join(sorted(ALLOWED_VALIDATION_STATUSES))
            ),
            errors=errors,
        )

    for field_name in REQUIRED_LIST_FIELDS:
        _validate_string_list(
            payload.get(field_name),
            label=field_name,
            errors=errors,
        )

    _validate_summary(payload.get("summary"), errors=errors)
    _validate_measured_facts(payload.get("measured_facts"), errors=errors)
    if enforce_live_measured_facts:
        _validate_live_measured_facts(
            payload.get("measured_facts"),
            root=root,
            errors=errors,
        )
    _validate_claim_sections(payload, root=root, errors=errors)
    _validate_claim_consistency(payload, root=root, errors=errors)
    _validate_validation_runs(
        payload.get("validation_runs"),
        root=root,
        errors=errors,
    )

    environment = payload.get("environment")
    if isinstance(environment, str) and environment.strip():
        _validate_deployment_notes(
            payload.get("deployment_notes"),
            environment=environment.strip(),
            errors=errors,
        )
    else:
        _expect(
            isinstance(payload.get("deployment_notes"), dict),
            "deployment_notes must be an object",
            errors=errors,
        )

    return errors


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify a checked-in codebase audit report JSON artifact."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root to validate against. Relative paths stay within the repo.",
    )
    parser.add_argument(
        "--report",
        required=True,
        help="Path to the audit report JSON artifact. Must resolve inside the repo root.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        root = resolve_cli_path_from_root(
            DEFAULT_ROOT,
            Path(args.root),
            field_name="root",
        )
        report_path = resolve_contained_repo_path_from_root(
            root,
            args.report,
            field_name="report",
        )
    except ValueError as exc:
        print(exc)
        return 2

    errors = verify_audit_report(
        root=root,
        report_path=report_path,
        enforce_live_measured_facts=True,
    )
    if errors:
        print("\n".join(errors))
        return 1

    print(f"audit report verified: {_label(report_path, root=root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
