# ADR-0005: Paystack as Primary Billing Processor

- Date: 2026-03-06
- Status: Accepted
- Owners: Billing, Finance, Platform

## Context

CloudSentinel serves a Nigeria-first and broader Africa-facing buyer set.
Billing needs fast local card/bank support, predictable settlement in local rails,
and low implementation overhead for launch velocity.

Stripe and Paystack were both evaluated for subscription billing, webhook
operations, retries, and operational supportability.

## Decision

Adopt Paystack as the primary billing processor for the current product phase.

Decision criteria and outcomes:

- Local market fit:
  - Paystack provides stronger default alignment for NGN flows and local payment
    operations used by our initial customer profile.
- Operational simplicity:
  - Existing billing domain integrations and operational runbooks already center
    on Paystack webhook and retry behavior.
- Time-to-market:
  - Staying on Paystack avoids a disruptive billing migration during ongoing
    platform hardening.

## Consequences

- Positive:
  - Faster onboarding for local customers.
  - Lower migration risk during current release cycles.
  - Better continuity with existing dunning and webhook controls.
- Tradeoffs:
  - Stripe-specific ecosystem features are deferred until a deliberate multi-processor
    strategy is approved.
  - International expansion may require a later dual-processor architecture.

## Review Trigger

Re-open this decision when either condition occurs:

1. Expansion requires processor coverage materially outside Paystack’s target rails.
2. Finance operations approve a dual-processor risk/cost model.

