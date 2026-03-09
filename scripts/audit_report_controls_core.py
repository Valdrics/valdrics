"""Core control checks for resolved audit report governance."""

from __future__ import annotations

import fnmatch
import shutil
import subprocess  # nosec B404 - controlled local git invocation only
from pathlib import Path

from scripts.verify_exception_governance import collect_exception_sites
from scripts.verify_python_module_size_budget import DEFAULT_MAX_LINES
from scripts.verify_test_to_production_ratio import (
    DEFAULT_MAX_TEST_TO_PRODUCTION_RATIO,
    validate_ratio,
)

ROOT_PROHIBITED_PATTERNS: tuple[str, ...] = (
    "artifact.json",
    "codealike.json",
    "coverage-enterprise-gate.xml",
    "inspect_httpx.py",
    "full_test_output.log",
    "test_results.log",
    "feedback.md",
    "useLanding.md",
    "test_*.sqlite",
    "test_*.sqlite-shm",
    "test_*.sqlite-wal",
)

PERSONAL_EMAIL_DOMAINS: frozenset[str] = frozenset(
    {
        "gmail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "icloud.com",
        "proton.me",
        "protonmail.com",
    }
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        cleaned = value.strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
            cleaned = cleaned[1:-1].strip()
        values[key] = cleaned
    return values


def is_git_tracked(repo_root: Path, path: str) -> bool:
    git_executable = shutil.which("git")
    if not git_executable:
        raise RuntimeError("git executable is required for repository hygiene checks")
    proc = subprocess.run(
        [git_executable, "ls-files", "--error-unmatch", path],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )  # nosec B603 - fixed git subcommand with repo-local path argument
    return proc.returncode == 0


def check_env_pool_values(env_values: dict[str, str]) -> tuple[str, ...]:
    errors: list[str] = []
    for key in ("DB_POOL_SIZE", "DB_MAX_OVERFLOW", "DB_POOL_TIMEOUT"):
        raw = env_values.get(key)
        if raw is None:
            errors.append(f"missing required env key: {key}")
            continue
        try:
            parsed = int(raw)
        except ValueError:
            errors.append(f"{key} must be integer (found {raw!r})")
            continue
        if parsed <= 0:
            errors.append(f"{key} must be > 0 (found {parsed})")
    return tuple(errors)


def check_root_file_absent(repo_root: Path, pattern: str) -> tuple[str, ...]:
    for child in repo_root.iterdir():
        if not child.is_file():
            continue
        if fnmatch.fnmatch(child.name, pattern):
            return (f"root file must be absent for pattern {pattern!r}",)
    return ()


def check_root_hygiene(repo_root: Path) -> tuple[str, ...]:
    errors: list[str] = []
    for child in repo_root.iterdir():
        if not child.is_file():
            continue
        for pattern in ROOT_PROHIBITED_PATTERNS:
            if fnmatch.fnmatch(child.name, pattern):
                errors.append(f"prohibited root artifact: {child.name} (pattern={pattern})")
                break
    return tuple(errors)


def check_c01(repo_root: Path) -> tuple[str, ...]:
    errors: list[str] = []
    if is_git_tracked(repo_root, ".env"):
        errors.append("`.env` is git-tracked; secrets must never be committed.")
    template_path = repo_root / ".env.example"
    if not template_path.exists():
        return ("missing .env.example template",)
    env_template = parse_env(template_path)
    if env_template.get("CSRF_SECRET_KEY", "").strip():
        errors.append("CSRF_SECRET_KEY in .env.example must be empty.")
    return tuple(errors)


def check_c02(repo_root: Path) -> tuple[str, ...]:
    template_path = repo_root / ".env.example"
    if not template_path.exists():
        return ("missing .env.example template",)
    env_template = parse_env(template_path)
    smtp_user = env_template.get("SMTP_USER", "").strip()
    errors: list[str] = []
    if smtp_user:
        errors.append("SMTP_USER in .env.example must be empty.")
        if "@" in smtp_user:
            domain = smtp_user.rsplit("@", 1)[-1].lower()
            if domain in PERSONAL_EMAIL_DOMAINS:
                errors.append(f"personal email domain forbidden for SMTP_USER: {domain}")
    return tuple(errors)


def check_c03(repo_root: Path) -> tuple[str, ...]:
    target = repo_root / "app/modules/enforcement/domain/service.py"
    if not target.exists():
        return (f"missing file: {target.as_posix()}",)
    lines = line_count(target)
    if lines > DEFAULT_MAX_LINES:
        return (f"{target.as_posix()} is {lines} lines (budget={DEFAULT_MAX_LINES})",)
    return ()


def check_h01(repo_root: Path) -> tuple[str, ...]:
    return check_root_file_absent(repo_root, "test_*.sqlite*")


def check_h02(repo_root: Path) -> tuple[str, ...]:
    scan_roots = tuple(
        path for path in (repo_root / "app", repo_root / "scripts") if path.exists()
    )
    sites = collect_exception_sites(roots=scan_roots)
    if not sites:
        return ()
    preview = ", ".join(site.key() for site in sites[:5])
    return (f"catch-all handlers must be zero; found {len(sites)} ({preview})",)


def check_h03(repo_root: Path) -> tuple[str, ...]:
    template_path = repo_root / ".env.example"
    if not template_path.exists():
        return ("missing .env.example template",)
    env_template = parse_env(template_path)
    errors: list[str] = []
    if env_template.get("APP_NAME", "").strip() != "Valdrics":
        errors.append("APP_NAME in .env.example must be exactly `Valdrics`.")
    cloudformation_url = env_template.get("CLOUDFORMATION_TEMPLATE_URL", "")
    if "valdrix" in cloudformation_url.lower():
        errors.append("CLOUDFORMATION_TEMPLATE_URL references old `valdrix` branding.")
    return tuple(errors)


def check_h04(repo_root: Path) -> tuple[str, ...]:
    budgets: dict[str, int] = {
        "app/modules/reporting/api/v1/costs.py": 1000,
        "app/modules/governance/api/v1/scim.py": 1000,
        "app/shared/core/notifications.py": 1000,
        "app/modules/governance/api/v1/settings/identity.py": 1000,
    }
    errors: list[str] = []
    for relative, max_lines in budgets.items():
        path = repo_root / relative
        if not path.exists():
            errors.append(f"missing file: {relative}")
            continue
        lines = line_count(path)
        if lines > max_lines:
            errors.append(f"{relative} is {lines} lines (budget={max_lines})")
    return tuple(errors)


def check_h05(repo_root: Path) -> tuple[str, ...]:
    template_path = repo_root / ".env.example"
    if not template_path.exists():
        return ("missing .env.example template",)
    return check_env_pool_values(parse_env(template_path))


def check_h06(repo_root: Path) -> tuple[str, ...]:
    workflow_path = repo_root / ".github/workflows/ci.yml"
    if not workflow_path.exists():
        return ("missing CI workflow .github/workflows/ci.yml",)
    workflow = read_text(workflow_path)
    required = (
        "uv run alembic upgrade head",
        "uv run alembic downgrade -1",
    )
    missing = [command for command in required if command not in workflow]
    if missing:
        return tuple(f"missing migration CI command: {command}" for command in missing)
    if workflow.count("uv run alembic upgrade head") < 2:
        return ("CI must run alembic upgrade head before and after downgrade.",)
    return ()


def check_h07(repo_root: Path) -> tuple[str, ...]:
    gate_path = repo_root / "scripts/run_enterprise_tdd_gate.py"
    gate_commands_path = repo_root / "scripts/enterprise_tdd_gate_commands.py"
    ratio_script_path = repo_root / "scripts/verify_test_to_production_ratio.py"
    errors: list[str] = []
    if not gate_path.exists():
        return ("missing enterprise gate runner script",)
    if not ratio_script_path.exists():
        return ("missing test-to-production ratio verifier script",)
    gate_text = read_text(gate_path)
    if gate_commands_path.exists():
        gate_text = gate_text + "\n" + read_text(gate_commands_path)
    required_tokens = (
        "--cov-report=xml:coverage-enterprise-gate.xml",
        "verify_coverage_subset_from_xml",
        "scripts/verify_test_to_production_ratio.py",
    )
    missing = [token for token in required_tokens if token not in gate_text]
    errors.extend(f"missing coverage-governance token: {token}" for token in missing)

    metrics, ratio_errors = validate_ratio(
        production_roots=(repo_root / "app", repo_root / "scripts"),
        tests_root=repo_root / "tests",
        max_ratio=DEFAULT_MAX_TEST_TO_PRODUCTION_RATIO,
    )
    errors.extend(ratio_errors)
    if not ratio_errors and metrics.production_lines > 0 and metrics.ratio >= 1.47:
        errors.append(
            "test-to-production ratio must improve versus report baseline 1.47:1; "
            f"current={metrics.ratio:.2f}:1"
        )
    return tuple(errors)


def check_h08(repo_root: Path) -> tuple[str, ...]:
    target = repo_root / "app/tasks/scheduler_tasks.py"
    if not target.exists():
        return (f"missing file: {target.as_posix()}",)
    lines = line_count(target)
    if lines > DEFAULT_MAX_LINES:
        return (f"{target.as_posix()} is {lines} lines (budget={DEFAULT_MAX_LINES})",)
    return ()
