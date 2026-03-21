from __future__ import annotations

import subprocess

import pytest

import scripts.verify_tenant_isolation as tenant_isolation_verifier
from scripts.verify_tenant_isolation import (
    DEFAULT_CHECKS,
    DEFAULT_TESTS,
    derive_evidence_checks,
    main,
    run_pytest,
)


def test_derive_evidence_checks_preserves_default_contract_for_default_suite() -> None:
    assert derive_evidence_checks(list(DEFAULT_TESTS)) == DEFAULT_CHECKS


def test_derive_evidence_checks_reports_custom_selectors_when_custom_suite_is_used() -> None:
    selectors = ["tests/unit/supply_chain/test_verify_jwt_bcp_checklist.py"]
    assert derive_evidence_checks(selectors) == selectors


def test_run_pytest_uses_repo_root_cwd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_run(cmd, *, cwd, check, capture_output, text):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["check"] = check
        captured["capture_output"] = capture_output
        captured["text"] = text
        return subprocess.CompletedProcess(cmd, 0, stdout="1 passed\n", stderr="")

    monkeypatch.setattr(tenant_isolation_verifier.subprocess, "run", _fake_run)
    monkeypatch.setattr(tenant_isolation_verifier, "_repo_root", lambda: "/repo-root")

    result = run_pytest(["tests/security/test_tenant_isolation_regression.py"])

    assert captured["cwd"] == "/repo-root"
    assert result["passed"] is True


def test_git_sha_uses_repo_root_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(cmd, *, cwd, check, capture_output, text):
        captured["cwd"] = cwd
        return subprocess.CompletedProcess(cmd, 0, stdout="deadbeef\n", stderr="")

    monkeypatch.setattr(tenant_isolation_verifier, "_resolve_executable", lambda _name: "/usr/bin/git")
    monkeypatch.setattr(tenant_isolation_verifier.subprocess, "run", _fake_run)
    monkeypatch.setattr(tenant_isolation_verifier, "_repo_root", lambda: "/repo-root")

    assert tenant_isolation_verifier._git_sha() == "deadbeef"
    assert captured["cwd"] == "/repo-root"


def test_main_accepts_argv_and_fails_on_empty_tests() -> None:
    with pytest.raises(SystemExit, match="No tests provided"):
        main(["--tests", ""])
