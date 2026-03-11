# Ops Docs

This directory is for active operational material only:
- release-gate evidence that is still referenced by scripts/tests
- operational contracts
- active runbooks and closure records that still inform current engineering work

Historical workstream registers, temporary landing/growth packs, and dated
change-categorization snapshots that no longer have repo references are archived
under `docs/archive/ops/2026-q1/`.

Run `uv run python3 scripts/verify_docs_archive_hygiene.py` before promoting new
dated operational docs into the active tree.

Active dated contracts that remain intentionally live include:
- `docs/ops/cloudflare_go_live_checklist_2026-03-02.md`
- `docs/ops/landing_funnel_alerting_2026-03-10.md`
