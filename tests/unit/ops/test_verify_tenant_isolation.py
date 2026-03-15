from __future__ import annotations

from scripts.verify_tenant_isolation import (
    DEFAULT_CHECKS,
    DEFAULT_TESTS,
    derive_evidence_checks,
)


def test_derive_evidence_checks_preserves_default_contract_for_default_suite() -> None:
    assert derive_evidence_checks(list(DEFAULT_TESTS)) == DEFAULT_CHECKS


def test_derive_evidence_checks_reports_custom_selectors_when_custom_suite_is_used() -> None:
    selectors = ["tests/unit/supply_chain/test_verify_jwt_bcp_checklist.py"]
    assert derive_evidence_checks(selectors) == selectors
