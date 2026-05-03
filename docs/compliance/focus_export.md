# FOCUS Export (v1.3 Core CSV)

Valdrics supports a **FOCUS v1.3-aligned core export** for cost records in the tenant ledger.

This export is intentionally scoped to the FOCUS columns that Valdrics can derive deterministically
from the normalized cost ledger today, without claiming SKU or unit-price conformance for fields
we do not persist yet.

## Endpoint

`GET /api/v1/costs/export/focus`

Query parameters:
- `start_date` (required): `YYYY-MM-DD` (inclusive)
- `end_date` (required): `YYYY-MM-DD` (inclusive)
- `provider` (optional): one of `aws|azure|gcp|saas|license|platform|hybrid|ai`
- `include_preliminary` (optional, default `false`): include `PRELIMINARY` records (otherwise exports `FINAL` only)

Auth / tier:
- Requires role: `admin` (or `owner`)
- Requires feature: `compliance_exports` (Pro+)

## Async Job Artifact

`JobType.COST_EXPORT` creates the same FOCUS v1.3 core CSV as a bounded inline
`background_jobs.result` artifact for scheduler-driven exports.

Payload fields:
- `start_date` (required): `YYYY-MM-DD` inclusive
- `end_date` (required): `YYYY-MM-DD` inclusive
- `format` (optional): `focus_v13_csv`
- `provider` (optional): one of `aws|azure|gcp|saas|license|platform|hybrid|ai`
- `include_preliminary` (optional, default `false`)
- `max_inline_bytes` (optional, default `1000000`, hard max `5000000`)

Oversized async exports fail explicitly until durable object storage is
configured; they do not return placeholder download URLs.

## Columns (Core)

The export includes the following columns:
- `AllocatedMethodDetails`
- `AllocatedMethodId`
- `AllocatedResourceId`
- `AllocatedResourceName`
- `AllocatedTags`
- `BilledCost`
- `BillingAccountId`
- `BillingAccountName`
- `BillingCurrency`
- `BillingPeriodStart`
- `BillingPeriodEnd`
- `ChargeCategory`
- `ChargeClass`
- `ChargeDescription`
- `ChargeFrequency`
- `ChargePeriodStart`
- `ChargePeriodEnd`
- `ConsumedQuantity`
- `ConsumedUnit`
- `ContractedCost`
- `EffectiveCost`
- `HostProviderName`
- `InvoiceIssuerName`
- `ListCost`
- `PricingCurrency`
- `PricingQuantity`
- `PricingUnit`
- `ProviderName`
- `PublisherName`
- `RegionId`
- `RegionName`
- `ResourceId`
- `ServiceProviderName`
- `ServiceCategory`
- `ServiceSubcategory`
- `ServiceName`
- `Tags`

## Semantics

- `BillingPeriodStart` is computed as the first day of the record month at `00:00:00Z`.
- `BillingPeriodEnd` is computed as the first day of the next month at `00:00:00Z`.
- For AWS/Azure/GCP records, `ChargePeriodStart` is the record timestamp and `ChargePeriodEnd` is `+1 hour`.
- For Cloud+ records (SaaS/license/platform/hybrid), `ChargePeriodStart/End` are daily window bounds.
- For AI records, `LLMUsage` rows are exported as FOCUS `AI and Machine Learning`
  / `Generative AI` usage with token quantity and persisted `cost_usd`.
- `ResourceId`, `ConsumedQuantity`, `ConsumedUnit`, `PricingQuantity`, and `PricingUnit` are emitted when the
  normalized ledger row contains resource/usage data.
- When canonical `CostAllocation` rows exist for a charge, the export emits one row per allocation split with
  `AllocatedMethodId=valdrics-rule-based-allocation-v1` and FOCUS-shaped `AllocatedMethodDetails`.
- A synthetic single `Unallocated` allocation row is treated as an origin charge, not as a split allocation.

## Known Limitations (By Design for v1)

- SKU/unit price columns are not included yet (Valdrics does not persist those fields in the ledger today).
- AI rows use the cost already persisted in `LLMUsage.cost_usd`; the export does not
  recalculate model pricing at export time.
- ServiceSubcategory is currently exported as `Other (ServiceCategory)` until per-provider subcategory
  normalization is added.
- `AllocatedTags` is reserved for provider-generated split allocation tags and is empty until upstream adapters
  supply allocation-specific tag sets distinct from resource tags.
