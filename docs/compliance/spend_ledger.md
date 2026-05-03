# Canonical Spend Ledger API

Valdrics exposes a canonical, tenant-scoped technology spend ledger for detailed
finance and FinOps review.

## Endpoint

`GET /api/v1/costs/ledger`

Query parameters:

- `start_date` (required): `YYYY-MM-DD` inclusive
- `end_date` (required): `YYYY-MM-DD` inclusive
- `provider` (optional): one of `aws|azure|gcp|saas|license|platform|hybrid|ai`
- `include_preliminary` (optional, default `false`): include `PRELIMINARY` records
- `limit` (optional, default `100`, max `500`)
- `offset` (optional, default `0`, max `10000`)

Auth / tier:

- Requires role: `admin` or `owner`
- Requires feature: `compliance_exports`

## Semantics

- `CostRecord` is the origin-charge ledger row.
- `CostAllocation` is the canonical split-allocation source.
- `LLMUsage` is projected into the same API contract as provider `ai`.
- Money and quantity fields are returned as fixed decimal strings, not floats.
- The endpoint is date-bounded, tenant-scoped, provider-filterable, and paginated.
- `allocation_status` is derived from canonical allocation rows:
  `allocated`, `partially_allocated`, or `unallocated`.
- `include_preliminary=false` exports only finalized ledger rows.
- Acceptance KPI ledger-quality evidence counts both normalized origin
  `CostRecord` rows and AI `LLMUsage` rows.

## FOCUS Export Relationship

- SKU/unit-price details are not emitted until provider adapters persist them.
- AI/LLM spend is also exported through the FOCUS CSV endpoint as provider `ai`.
