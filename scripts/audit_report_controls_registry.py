"""Registry and non-core controls for resolved audit report governance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from scripts.audit_report_controls_core import (
    check_c01,
    check_c02,
    check_c03,
    check_h01,
    check_h02,
    check_h03,
    check_h04,
    check_h05,
    check_h06,
    check_h07,
    check_h08,
    check_root_file_absent,
    check_root_hygiene,
    line_count,
    read_text,
)
from scripts.verify_adapter_test_coverage import find_uncovered_adapters
from scripts.verify_python_module_size_budget import DEFAULT_MAX_LINES

FINDING_ORDER: tuple[str, ...] = (
    "C-01",
    "C-02",
    "C-03",
    "H-01",
    "H-02",
    "H-03",
    "H-04",
    "H-05",
    "H-06",
    "H-07",
    "H-08",
    "M-01",
    "M-02",
    "M-03",
    "M-04",
    "M-05",
    "M-06",
    "M-07",
    "M-08",
    "M-09",
    "M-10",
    "L-01",
    "L-02",
    "L-03",
    "L-04",
    "L-05",
    "L-06",
)

OPTIMIZATION_MAX_SOURCE_FILES = 105
OPTIMIZATION_WRAPPER_FILES: tuple[str, ...] = (
    "app/modules/optimization/domain/base.py",
    "app/modules/optimization/domain/detector.py",
    "app/modules/optimization/domain/remediation_service.py",
    "app/modules/optimization/domain/zombie_plugin.py",
    "app/modules/optimization/domain/aws_provider/__init__.py",
    "app/modules/optimization/domain/aws_provider/detector.py",
    "app/modules/optimization/domain/aws_provider/plugins.py",
    "app/modules/optimization/domain/aws_provider/plugins/__init__.py",
    "app/modules/optimization/domain/aws_provider/plugins/compute.py",
    "app/modules/optimization/domain/azure_provider/__init__.py",
    "app/modules/optimization/domain/azure_provider/detector.py",
    "app/modules/optimization/domain/azure_provider/plugins.py",
    "app/modules/optimization/domain/gcp_provider/__init__.py",
    "app/modules/optimization/domain/gcp_provider/detector.py",
    "app/modules/optimization/domain/gcp_provider/plugins.py",
)


@dataclass(frozen=True)
class FindingDefinition:
    finding_id: str
    title: str
    check: Callable[[Path], tuple[str, ...]]


def check_m01(repo_root: Path) -> tuple[str, ...]:
    errors: list[str] = []
    gate_path = repo_root / "scripts/verify_python_module_size_budget.py"
    if not gate_path.exists():
        return ("missing module-size governance script",)
    text = read_text(gate_path)
    if "DEFAULT_MAX_LINES = 700" not in text:
        errors.append("default module-size hard budget must remain 700 lines.")
    if "PREFERRED_MAX_LINES = 500" not in text:
        errors.append("preferred module-size target must remain 500 lines.")
    if "max(default_max_lines, override_budget)" not in text:
        errors.append(
            "module-size overrides must be floor-aware (cannot enforce lower-than-default budgets)."
        )
    if "MODULE_LINE_BUDGET_OVERRIDES: dict[str, int] = {}" not in text:
        errors.append("module-size override table must be empty unless a current hard-budget exception is required.")
    if 'default="strict"' not in text:
        errors.append(
            "module-size governance must default to strict mode so hard-budget drift blocks merges."
        )

    ci_path = repo_root / ".github/workflows/ci.yml"
    if ci_path.exists():
        ci_text = read_text(ci_path)
        if "--select C901" not in ci_text:
            errors.append("python complexity governance step (ruff C901) must remain enabled.")

    optimization_root = repo_root / "app/modules/optimization"
    source_files = tuple(sorted(optimization_root.rglob("*.py")))
    if len(source_files) > OPTIMIZATION_MAX_SOURCE_FILES:
        errors.append(
            "optimization module must stay within the structural budget: "
            f"{len(source_files)} files (budget={OPTIMIZATION_MAX_SOURCE_FILES})"
        )
    for wrapper_path in OPTIMIZATION_WRAPPER_FILES:
        if (repo_root / wrapper_path).exists():
            errors.append(f"legacy optimization wrapper must be removed: {wrapper_path}")
    return tuple(errors)


def check_m02(repo_root: Path) -> tuple[str, ...]:
    missing = find_uncovered_adapters(
        adapters_root=repo_root / "app/shared/adapters",
        tests_root=repo_root / "tests",
    )
    if not missing:
        return ()
    return tuple(f"adapter missing test reference: {name}" for name in missing)


def check_m03(repo_root: Path) -> tuple[str, ...]:
    target = repo_root / "app/modules/governance/domain/security/compliance_pack_bundle.py"
    if not target.exists():
        return (f"missing file: {target.as_posix()}",)
    lines = line_count(target)
    if lines > DEFAULT_MAX_LINES:
        return (f"{target.as_posix()} is {lines} lines (budget={DEFAULT_MAX_LINES})",)
    return ()


def check_m04(repo_root: Path) -> tuple[str, ...]:
    target = repo_root / "app/py.typed"
    if not target.exists():
        return ("missing app/py.typed marker file",)
    return ()


def check_m05(repo_root: Path) -> tuple[str, ...]:
    return check_h03(repo_root)


def check_m06(repo_root: Path) -> tuple[str, ...]:
    workflow_path = repo_root / ".github/workflows/ci.yml"
    if not workflow_path.exists():
        return ("missing CI workflow .github/workflows/ci.yml",)
    workflow = read_text(workflow_path).lower()
    required_tokens = ("aquasecurity/trivy-action", "trivy")
    missing = [token for token in required_tokens if token not in workflow]
    return tuple(f"missing CVE scanning token: {token}" for token in missing)


def check_m07(repo_root: Path) -> tuple[str, ...]:
    return check_root_file_absent(repo_root, "inspect_httpx.py")


def check_m08(repo_root: Path) -> tuple[str, ...]:
    target = repo_root / "docs/architecture/database_schema_overview.md"
    if not target.exists():
        return ("missing schema documentation: docs/architecture/database_schema_overview.md",)
    return ()


def check_m09(repo_root: Path) -> tuple[str, ...]:
    path = repo_root / "app/shared/llm/analyzer.py"
    if not path.exists():
        return (f"missing file: {path.as_posix()}",)
    lines = line_count(path)
    text = read_text(path)
    errors: list[str] = []
    if lines > 1000:
        errors.append(f"{path.as_posix()} is {lines} lines (budget=1000)")
    required_tokens = (
        "FINOPS_ANALYSIS_SCHEMA_VERSION",
        "FINOPS_PROMPT_FALLBACK_VERSION",
        "FINOPS_RESPONSE_NORMALIZER_VERSION",
        "LLMGuardrails.validate_output",
        "prompt_version",
    )
    for token in required_tokens:
        if token not in text:
            errors.append(f"analyzer missing required governance token: {token}")
    return tuple(errors)


def check_m10(repo_root: Path) -> tuple[str, ...]:
    return check_root_file_absent(repo_root, "feedback.md")


def check_l01(repo_root: Path) -> tuple[str, ...]:
    return check_root_file_absent(repo_root, "artifact.json")


def check_l02(repo_root: Path) -> tuple[str, ...]:
    duplicates = (
        "scripts/check_db.py",
        "scripts/check_db_tables.py",
        "scripts/db_check.py",
        "scripts/db_deep_dive.py",
        "scripts/analyze_tables.py",
    )
    errors: list[str] = []
    for duplicate in duplicates:
        if (repo_root / duplicate).exists():
            errors.append(f"duplicate DB diagnostic script must be removed: {duplicate}")
    if not (repo_root / "scripts/db_diagnostics.py").exists():
        errors.append("missing canonical DB diagnostics entrypoint: scripts/db_diagnostics.py")
    return tuple(errors)


def check_l03(repo_root: Path) -> tuple[str, ...]:
    errors: list[str] = []
    if (repo_root / "codealike.json").exists():
        errors.append("codealike.json must not exist in repository root.")
    gitignore = repo_root / ".gitignore"
    if not gitignore.exists():
        errors.append("missing .gitignore")
    elif "codealike.json" not in read_text(gitignore):
        errors.append(".gitignore must include `codealike.json`.")
    return tuple(errors)


def check_l04(repo_root: Path) -> tuple[str, ...]:
    return check_root_file_absent(repo_root, "useLanding.md")


def check_l05(repo_root: Path) -> tuple[str, ...]:
    errors = list(check_root_file_absent(repo_root, "full_test_output.log"))
    errors.extend(check_root_file_absent(repo_root, "test_results.log"))
    return tuple(errors)


def check_l06(repo_root: Path) -> tuple[str, ...]:
    return check_root_file_absent(repo_root, "coverage-enterprise-gate.xml")


FINDING_DEFINITIONS: tuple[FindingDefinition, ...] = (
    FindingDefinition("C-01", "CSRF secret committed in .env", check_c01),
    FindingDefinition("C-02", "Personal SMTP config", check_c02),
    FindingDefinition("C-03", "God-object enforcement service", check_c03),
    FindingDefinition("H-01", "Orphaned sqlite artifacts", check_h01),
    FindingDefinition("H-02", "Broad catch-all exception usage", check_h02),
    FindingDefinition("H-03", "Old branding in environment config", check_h03),
    FindingDefinition("H-04", "Oversized API controller modules", check_h04),
    FindingDefinition("H-05", "Missing DB pool controls", check_h05),
    FindingDefinition("H-06", "Migration rollback CI guard", check_h06),
    FindingDefinition("H-07", "Coverage and test-ratio governance signal", check_h07),
    FindingDefinition("H-08", "Oversized scheduler tasks module", check_h08),
    FindingDefinition("M-01", "Optimization scope guardrail", check_m01),
    FindingDefinition("M-02", "Adapter test coverage unknown", check_m02),
    FindingDefinition("M-03", "Oversized compliance bundle", check_m03),
    FindingDefinition("M-04", "Missing py.typed marker", check_m04),
    FindingDefinition("M-05", "Old branding template URL", check_m05),
    FindingDefinition("M-06", "Missing image CVE scan", check_m06),
    FindingDefinition("M-07", "Debug utility in repository root", check_m07),
    FindingDefinition("M-08", "Missing schema documentation", check_m08),
    FindingDefinition("M-09", "LLM analyzer governance controls", check_m09),
    FindingDefinition("M-10", "Feedback artifact in repository root", check_m10),
    FindingDefinition("L-01", "artifact.json root debris", check_l01),
    FindingDefinition("L-02", "Database diagnostics script duplication", check_l02),
    FindingDefinition("L-03", "codealike root artifact", check_l03),
    FindingDefinition("L-04", "useLanding root artifact", check_l04),
    FindingDefinition("L-05", "committed test output logs", check_l05),
    FindingDefinition("L-06", "coverage artifact in root", check_l06),
)

FINDING_INDEX: dict[str, FindingDefinition] = {
    definition.finding_id: definition for definition in FINDING_DEFINITIONS
}


def run_checks(
    *,
    repo_root: Path,
    finding_ids: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    failures: list[str] = []
    passes: list[str] = []

    root_hygiene_errors = check_root_hygiene(repo_root)
    if root_hygiene_errors:
        failures.extend(f"[root-hygiene] {error}" for error in root_hygiene_errors)

    for finding_id in finding_ids:
        definition = FINDING_INDEX[finding_id]
        errors = definition.check(repo_root)
        if errors:
            failures.extend(f"[{finding_id}] {error}" for error in errors)
            continue
        passes.append(finding_id)
    return tuple(failures), tuple(passes)
