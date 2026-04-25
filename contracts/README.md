# Contracts

This directory holds machine-readable contract artifacts that are intended to be validated by tooling.

Layout:

- `contracts/schemas/`
  - canonical JSON Schemas
- `contracts/examples/`
  - example YAML and JSON manifests that validate against those schemas

Repository convention:

- human-facing product or strategy prose belongs in `docs/`
- machine-readable contract payloads belong here
- operational `.yml` and `.yaml` files stay with the owning subsystem
  - for example `prometheus/`, `grafana/`, `cloudformation/`, or workflow directories

Current contract families:

- `Technology Value Contract (TVC)`
- `Execution Receipt`

Managed deployment examples:

- `contracts/examples/unified-platform-deploy-staging.yaml`
- `contracts/examples/unified-platform-deploy-production.yaml`
