# Ops Docs

This directory is for active operational material only:
- release-gate evidence that is still referenced by scripts/tests
- operational contracts
- active runbooks and closure records that still inform current engineering work

Historical workstream registers, temporary landing/growth packs, and dated
change-categorization snapshots that no longer have repo references are archived
under `docs/archive/ops/2026-q1/`. Historical promotion packets are archived
under `docs/archive/evidence/`.

Run `uv run python3 scripts/verify_docs_archive_hygiene.py` before promoting new
dated operational docs into the active tree.

A dated file stays live only when it is explicitly registered in
`scripts/verify_docs_archive_hygiene.py`; repo references alone are not
sufficient.

The current intentionally live dated surface is a closed, verifier-enforced set
covering:
- current enforcement control/release-gate docs under `docs/ops/`
- current dated release-gate evidence artifacts under `docs/ops/evidence/` and
  `docs/security/`

Persistent operational contracts should use undated canonical paths. Example:
- `docs/ops/landing_funnel_alerting.md`
- `docs/ops/alert-evidence.md`
- `docs/ops/feature_enforceability_matrix.json`
- `docs/ops/enforcement_stress_evidence.md`
- `docs/ops/enforcement_post_closure_sanity.md`
- `docs/ops/enforcement_failure_injection_matrix.md`
- `docs/ops/benchmark_alignment_profiles.md`
- `docs/security/jwt_bcp_checklist.json`
- `docs/security/ssdf_traceability_matrix.json`
