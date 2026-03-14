# All Changes Categorization (2026-03-14)

Snapshot:
- Captured at: `2026-03-14T04:30:09Z`
- Base commit: `342b9939f50b76df99c2f61874f4d303ba1f37f0`
- Pending paths: `36`
- Branch at snapshot: `fix/main-trivy-pyjwt-2026-03-14`

## Track BE: Security and Release-Gate Hardening
Scope:
- Close push-only container CVE failure by raising the backend JWT floor to the patched release.
- Keep release-gate command contracts explicit for image-pinning checks.
- Remove examples that encourage unsafe token bootstrap paths.

Paths:
- `pyproject.toml`
- `uv.lock`
- `scripts/enterprise_tdd_gate_commands.py`
- `scripts/load_test_api.py`
- `tests/unit/supply_chain/test_enterprise_tdd_gate_runner.py`

Notes:
- `PyJWT` is raised from `2.11.0` to `2.12.1` to clear the Trivy finding for `CVE-2026-32597`.
- Release-gate image pinning commands now export explicit `REGISTRY` and `VERSION` inputs.

## Track BF: Evidence, Disposition, and Incident Response Contracts
Scope:
- Strengthen evidence capture/token sanitation.
- Add runtime probe linkage to the disposition register and freshness verification.
- Tighten acceptance-evidence failure handling and update the incident runbook to the guarded emergency disconnect flow.

Paths:
- `app/shared/core/evidence_capture.py`
- `docs/ops/evidence/valdrics_disposition_register_2026-02-28.json`
- `docs/ops/evidence/valdrics_disposition_register_TEMPLATE.json`
- `docs/ops/incident_response_runbook.md`
- `scripts/capture_acceptance_evidence.py`
- `scripts/verify_valdrics_disposition_freshness.py`
- `tests/unit/ops/test_capture_acceptance_evidence_script.py`
- `tests/unit/ops/test_runtime_evidence_generators.py`
- `tests/unit/ops/test_verify_valdrics_disposition_freshness.py`

Notes:
- Disposition artifacts now carry `runtime_probe_results` and per-finding `control_probe_ids`.
- Acceptance evidence exits non-zero when required bundle members are incomplete.

## Track BG: Legacy Ops Script Hardening and RLS Utilities
Scope:
- Harden destructive or high-risk operator scripts with explicit break-glass validation.
- Retire unsafe dev bearer-token generation paths.
- Centralize RLS table-filter helpers and make purge/remediation tooling deterministic.

Paths:
- `scripts/audit_schema.py`
- `scripts/cleanup_partitions.py`
- `scripts/db_diagnostics.py`
- `scripts/deactivate_aws.py`
- `scripts/delete_cloudfront.py`
- `scripts/dev_bearer_token.py`
- `scripts/disable_cloudfront.py`
- `scripts/emergency_disconnect.py`
- `scripts/list_partitions.py`
- `scripts/purge_simulation_data.py`
- `scripts/remediate_rls_gaps.py`
- `scripts/rls_tooling.py`
- `scripts/seed_final.py`
- `scripts/supabase_cleanup.py`
- `scripts/update_exchange_rates.py`
- `scripts/verify_rls.py`
- `tests/unit/ops/test_db_diagnostics.py`
- `tests/unit/ops/test_legacy_script_hardening.py`

Notes:
- New `scripts/emergency_disconnect.py` performs Valdrics-side AWS disconnect only; cloud-side revocation remains manual.
- `scripts/purge_simulation_data.py` is converted to explicit tenant-targeted dry-run-by-default purge logic.
- `scripts/rls_tooling.py` avoids duplicated exempt-table logic across legacy scripts.

## Track BH: Runtime Operations Verification and Managed Failover
Scope:
- Strengthen regional failover and container-image pinning verifiers.
- Keep runtime disposition freshness aligned with ops evidence generation.

Paths:
- `scripts/run_regional_failover.py`
- `scripts/verify_container_image_pinning.py`
- `tests/unit/ops/test_run_regional_failover.py`
- `tests/unit/ops/test_verify_container_image_pinning.py`

Notes:
- This track is intentionally small and operational; it complements the broader script-hardening work without duplicating it.

## Batching Decision
Decision:
- Merge as one consolidated PR.

Reasoning:
- The changes are operationally related and mostly touch scripts, evidence contracts, and release-gate behavior.
- Splitting the batch would create duplicate issue/PR overhead with little review benefit because the changed surfaces are all maintenance and safety tooling, not product runtime features.
