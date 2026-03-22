from __future__ import annotations

import os
from pathlib import Path

import pytest

import scripts.verify_audit_report_resolved as audit_report_verifier
from scripts.verify_audit_report_resolved import (
    main,
    parse_report_findings,
    validate_generic_report_findings,
    validate_report_scope,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_lines(path: Path, count: int) -> None:
    body = "\n".join(f"line_{idx}" for idx in range(count))
    _write(path, body)


def test_parse_report_findings_extracts_ids(tmp_path: Path) -> None:
    report = tmp_path / "audit.md"
    _write(
        report,
        "\n".join(
            [
                "### C-01: Secret leak",
                "### H-02: Catch-all handlers",
                "### M-09: Analyzer governance",
                "### L-02: Script duplication",
            ]
        ),
    )

    assert parse_report_findings(report) == ("C-01", "H-02", "M-09", "L-02")


def test_validate_report_scope_flags_missing_findings() -> None:
    errors = validate_report_scope(
        report_findings=("C-01", "H-01"),
        expected_findings=("C-01", "H-01", "L-02"),
    )
    assert errors == ("report missing expected finding headings: L-02",)


def test_validate_generic_report_findings_flags_duplicates() -> None:
    errors = validate_generic_report_findings(
        report_findings=("PERF-01", "TECH-01", "PERF-01"),
    )
    assert errors == ("report has duplicate finding headings: PERF-01",)


def test_main_allows_noncanonical_report_headings(tmp_path: Path) -> None:
    report = tmp_path / "deep_debt.md"
    _write(
        report,
        "\n".join(
            [
                "### TECH-01: Dynamic import usage",
                "### OPS-01: Environment drift",
            ]
        ),
    )
    _write(
        tmp_path / ".env.example",
        "\n".join(
            [
                'APP_NAME="Valdrics"',
                "CSRF_SECRET_KEY=",
                "SMTP_USER=",
                "DB_POOL_SIZE=20",
                "DB_MAX_OVERFLOW=10",
                "DB_POOL_TIMEOUT=30",
            ]
        ),
    )

    exit_code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--report-path",
            str(report),
            "--finding",
            "C-01",
        ]
    )

    assert exit_code == 0


def test_main_passes_for_c01_with_clean_template(tmp_path: Path) -> None:
    _write(
        tmp_path / ".env.example",
        "\n".join(
            [
                'APP_NAME="Valdrics"',
                "CSRF_SECRET_KEY=",
                "SMTP_USER=",
                "DB_POOL_SIZE=20",
                "DB_MAX_OVERFLOW=10",
                "DB_POOL_TIMEOUT=30",
            ]
        ),
    )

    exit_code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--skip-report-check",
            "--finding",
            "C-01",
        ]
    )

    assert exit_code == 0


def test_main_flags_l02_duplicate_scripts(tmp_path: Path) -> None:
    _write(tmp_path / ".env.example", "CSRF_SECRET_KEY=\nSMTP_USER=\n")
    _write(tmp_path / "scripts/check_db.py", "print('legacy')\n")
    _write(tmp_path / "scripts/db_diagnostics.py", "print('new')\n")

    exit_code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--skip-report-check",
            "--finding",
            "L-02",
        ]
    )

    assert exit_code == 1


def test_main_resolves_relative_repo_root_from_repo_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(audit_report_verifier.__file__).resolve().parents[1]
    captured: dict[str, Path] = {}

    def _capture_run_checks(*, repo_root: Path, finding_ids: tuple[str, ...]):
        captured["repo_root"] = repo_root
        captured["finding_ids"] = Path  # sentinel to prove call executed
        return (), ("ok",)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(audit_report_verifier, "run_checks", _capture_run_checks)

    assert main(["--repo-root", ".", "--skip-report-check", "--finding", "C-01"]) == 0
    assert captured["repo_root"] == repo_root


def test_main_resolves_relative_report_path_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(audit_report_verifier.__file__).resolve().parents[1]
    report_path = repo_root / "tmp-relative-audit-report.md"
    _write(report_path, "### C-01: Example finding\n")

    def _capture_run_checks(*, repo_root: Path, finding_ids: tuple[str, ...]):
        return (), ("ok",)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(audit_report_verifier, "run_checks", _capture_run_checks)
    try:
        assert (
            main(
                [
                    "--repo-root",
                    ".",
                    "--report-path",
                    report_path.name,
                    "--finding",
                    "C-01",
                ]
            )
            == 0
        )
    finally:
        report_path.unlink(missing_ok=True)


def test_main_rejects_relative_repo_root_repo_escape() -> None:
    assert main(["--repo-root", os.path.join("..", ".."), "--skip-report-check"]) == 2


def test_main_rejects_relative_report_path_repo_escape(tmp_path: Path) -> None:
    repo_root = Path(audit_report_verifier.__file__).resolve().parents[1]
    outside_report = tmp_path / "outside.md"
    _write(outside_report, "### C-01: Example finding\n")

    assert (
        main(
            [
                "--repo-root",
                str(repo_root),
                "--report-path",
                os.path.relpath(outside_report, repo_root),
                "--finding",
                "C-01",
            ]
        )
        == 2
    )


def test_main_flags_m09_missing_governance_tokens(tmp_path: Path) -> None:
    _write(tmp_path / ".env.example", "CSRF_SECRET_KEY=\nSMTP_USER=\n")
    _write(tmp_path / "app/shared/llm/analyzer.py", "def analyze():\n    return {}\n")

    exit_code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--skip-report-check",
            "--finding",
            "M-09",
        ]
    )

    assert exit_code == 1


def test_main_passes_m01_with_compact_optimization_structure(tmp_path: Path) -> None:
    _write(
        tmp_path / "scripts/verify_python_module_size_budget.py",
        (
            "DEFAULT_MAX_LINES = 700\n"
            "PREFERRED_MAX_LINES = 500\n"
            "MODULE_LINE_BUDGET_OVERRIDES: dict[str, int] = {}\n"
            "override_budget = 700\n"
            "max(default_max_lines, override_budget)\n"
            "default=\"strict\"\n"
        ),
    )
    _write(tmp_path / "app/modules/optimization/domain/service.py", "pass\n")

    exit_code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--skip-report-check",
            "--finding",
            "M-01",
        ]
    )
    assert exit_code == 0


def test_main_flags_m01_when_file_budget_exceeded(tmp_path: Path) -> None:
    _write(
        tmp_path / "scripts/verify_python_module_size_budget.py",
        (
            "DEFAULT_MAX_LINES = 700\n"
            "PREFERRED_MAX_LINES = 500\n"
            "MODULE_LINE_BUDGET_OVERRIDES: dict[str, int] = {}\n"
            "override_budget = 700\n"
            "max(default_max_lines, override_budget)\n"
            "default=\"strict\"\n"
        ),
    )
    for idx in range(106):
        _write(
            tmp_path / f"app/modules/optimization/domain/generated_{idx}.py",
            "pass\n",
        )

    exit_code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--skip-report-check",
            "--finding",
            "M-01",
        ]
    )
    assert exit_code == 1


def test_main_ignores_optimization_package_markers_for_m01(tmp_path: Path) -> None:
    _write(
        tmp_path / "scripts/verify_python_module_size_budget.py",
        (
            "DEFAULT_MAX_LINES = 700\n"
            "PREFERRED_MAX_LINES = 500\n"
            "MODULE_LINE_BUDGET_OVERRIDES: dict[str, int] = {}\n"
            "override_budget = 700\n"
            "max(default_max_lines, override_budget)\n"
            "default=\"strict\"\n"
        ),
    )
    for idx in range(105):
        _write(
            tmp_path / f"app/modules/optimization/domain/generated_{idx}.py",
            "pass\n",
        )
    for package in (
        "app/modules/optimization/__init__.py",
        "app/modules/optimization/domain/__init__.py",
        "app/modules/optimization/adapters/__init__.py",
    ):
        _write(tmp_path / package, "")

    exit_code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--skip-report-check",
            "--finding",
            "M-01",
        ]
    )

    assert exit_code == 0


def test_main_flags_m03_when_bundle_exceeds_default_budget(tmp_path: Path) -> None:
    _write_lines(
        tmp_path / "app/modules/governance/domain/security/compliance_pack_bundle.py",
        701,
    )

    exit_code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--skip-report-check",
            "--finding",
            "M-03",
        ]
    )
    assert exit_code == 1


def test_main_passes_h07_with_ratio_governance_and_improved_ratio(tmp_path: Path) -> None:
    _write(
        tmp_path / "scripts/run_enterprise_tdd_gate.py",
        "\n".join(
            [
                "--cov-report=xml:coverage-enterprise-gate.xml",
                "verify_coverage_subset_from_xml",
                "scripts/verify_test_to_production_ratio.py",
            ]
        ),
    )
    _write(tmp_path / "scripts/verify_test_to_production_ratio.py", "pass\n")
    _write_lines(tmp_path / "app/service.py", 100)
    _write_lines(tmp_path / "tests/test_service.py", 120)

    exit_code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--skip-report-check",
            "--finding",
            "H-07",
        ]
    )

    assert exit_code == 0


def test_main_flags_h07_when_ratio_exceeds_budget(tmp_path: Path) -> None:
    _write(
        tmp_path / "scripts/run_enterprise_tdd_gate.py",
        "\n".join(
            [
                "--cov-report=xml:coverage-enterprise-gate.xml",
                "verify_coverage_subset_from_xml",
                "scripts/verify_test_to_production_ratio.py",
            ]
        ),
    )
    _write(tmp_path / "scripts/verify_test_to_production_ratio.py", "pass\n")
    _write_lines(tmp_path / "app/service.py", 50)
    _write_lines(tmp_path / "tests/test_service.py", 100)

    exit_code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--skip-report-check",
            "--finding",
            "H-07",
        ]
    )

    assert exit_code == 1


def test_main_rejects_non_directory_repo_root(tmp_path: Path) -> None:
    repo_root_file = tmp_path / "repo-root.txt"
    repo_root_file.write_text("not-a-directory\n", encoding="utf-8")

    exit_code = main(
        [
            "--repo-root",
            str(repo_root_file),
            "--skip-report-check",
            "--finding",
            "C-01",
        ]
    )

    assert exit_code == 2


def test_main_rejects_directory_report_path(tmp_path: Path) -> None:
    report_dir = tmp_path / "report-dir"
    report_dir.mkdir()
    _write(
        tmp_path / ".env.example",
        "\n".join(
            [
                'APP_NAME="Valdrics"',
                "CSRF_SECRET_KEY=",
                "SMTP_USER=",
                "DB_POOL_SIZE=20",
                "DB_MAX_OVERFLOW=10",
                "DB_POOL_TIMEOUT=30",
            ]
        ),
    )

    exit_code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--report-path",
            str(report_dir),
            "--finding",
            "C-01",
        ]
    )

    assert exit_code == 2
