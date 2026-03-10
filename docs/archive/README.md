# Documentation Archive

This directory holds repository history that is no longer part of the active
runtime, release-gate, compliance-evidence, or operator-runbook surface.

Archive rules:
- Keep active runbooks, contracts, compliance artifacts, and evidence packs in
  their live locations under `docs/`.
- Move dated research notes, workstream split registers, temporary launch packs,
  and one-off implementation snapshots here once they are no longer referenced
  by code, tests, or verification scripts.
- Keep active reference/security/governance documents in the live docs tree even
  when they are not code-referenced, if they still describe current policy,
  threat posture, or operating assumptions.
- Archive duplicate top-level reference/runbook material when an active version
  already exists elsewhere in `docs/` and the duplicate no longer participates
  in runtime or verification contracts.
- Prefer archiving over deletion unless the material is duplicated elsewhere and
  has no ongoing governance or historical value.
