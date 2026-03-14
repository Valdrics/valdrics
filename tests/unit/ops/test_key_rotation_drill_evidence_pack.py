from __future__ import annotations

from pathlib import Path

from scripts.verify_key_rotation_drill_evidence import verify_key_rotation_drill_evidence


REPO_ROOT = Path(__file__).resolve().parents[3]
DRILL_PATH = REPO_ROOT / "docs/ops/key-rotation-drill-2026-02-27.md"


def test_key_rotation_drill_pack_has_required_evidence_markers() -> None:
    raw = DRILL_PATH.read_text(encoding="utf-8")
    required_snippets = (
        "drill_id:",
        "executed_at_utc:",
        "owner:",
        "approver:",
        "next_drill_due_on:",
        "source_pre_rotation_tokens_accepted:",
        "source_post_rotation_new_tokens_accepted:",
        "source_rollback_validation_passed:",
        "fallback_verification_passed: true",
        "rollback_validation_passed: true",
        "post_drill_status: PASS",
        "test_consume_approval_token_accepts_primary_secret",
        "test_consume_approval_token_accepts_new_primary_secret_after_rotation",
        "test_consume_approval_token_accepts_rollback_fallback_secret",
    )
    for snippet in required_snippets:
        assert snippet in raw


def test_key_rotation_drill_pack_validates_against_contract() -> None:
    exit_code = verify_key_rotation_drill_evidence(
        drill_path=DRILL_PATH,
        max_drill_age_days=120.0,
    )
    assert exit_code == 0
