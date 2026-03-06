# ADR-0006: Supabase Managed Auth over Self-Hosted Identity Stack

- Date: 2026-03-06
- Status: Accepted
- Owners: Security, Platform, Product

## Context

The platform requires secure tenant authentication, token issuance, and
database-level access controls with minimal operational overhead.
Two options were considered:

1. Managed Supabase auth + database integration.
2. Self-hosted auth/identity platform operated directly by the engineering team.

## Decision

Use Supabase managed auth as the primary identity platform for this phase.

Rationale:

- Delivery and security posture:
  - Supabase auth integrates directly with Postgres/RLS workflows used across
    the product.
- Operational load:
  - Managed auth reduces custom identity infrastructure and incident burden
    during core product hardening.
- Team focus:
  - Engineering effort stays concentrated on FinOps differentiation rather than
    building a bespoke identity stack.

## Consequences

- Positive:
  - Faster delivery with lower identity operations burden.
  - Clear integration boundary for auth/session behavior.
- Tradeoffs:
  - Vendor dependency for core auth lifecycle.
  - Future requirements may demand migration planning if asymmetric/self-issued
    token ownership is required.

## Review Trigger

Re-open this decision when either condition occurs:

1. Compliance scope requires identity controls beyond current managed boundaries.
2. Product roadmap demands self-hosted or multi-IdP issuer ownership.

