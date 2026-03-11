# Licensing Guide

Last updated: March 11, 2026

This project is released under the Business Source License 1.1
(`BUSL-1.1`, commonly called `BSL 1.1`). The legal source of truth is
`LICENSE`. If anything in this guide conflicts with `LICENSE`, the `LICENSE`
file wins.

## Plain-English Summary

- You can run Valdrics internally in your own organization.
- You can operate a customer-owned or customer-controlled instance for that
  customer's internal business operations.
- You cannot offer Valdrics itself as a competing hosted or managed service to
  third parties under the default repository license.
- On the change date, the code converts to Apache 2.0.
- The repository being public on GitHub does not make it OSI open source today.

## Change Terms

- Change Date: January 5, 2030
- Change License: Apache License 2.0
- Current repository policy anchors that date to the first public repository
  history on January 5, 2026.

## Allowed and Prohibited Use Matrix

| Scenario | Allowed | Notes |
| --- | --- | --- |
| Internal self-hosting for your own company | Yes | Includes production internal usage under the Additional Use Grant. |
| Internal use by subsidiaries under same corporate control | Yes | Treated as internal use under the Additional Use Grant. |
| Consulting/professional services deploying a customer-owned or customer-controlled instance | Yes | Allowed where the customer's internal operations are the beneficiary. |
| Reselling Valdrics as your own hosted SaaS | No | Prohibited competitive hosted offering. |
| Multi-tenant MSP offering Valdrics capabilities as a service | No | Prohibited if customers consume Valdrics as the service. |
| Research, evaluation, and test environments | Yes | Non-production use is allowed under the base BUSL terms. |

## Definitions Used in This Project

- Production use: any environment used to serve real internal business workloads.
- Hosted service: software operated by one party for use by unrelated third parties over a network.
- Competitive offering: hosted use where Valdrics functionality is sold or bundled as a service.

## Licensing FAQ

### Can I self-host Valdrics?

Yes, for your own internal operations.

### Can Valdrics-AI offer an official hosted SaaS?

Yes. The BUSL/BSL restriction targets third parties offering competing hosted
services. It does not block the project owner from operating the official
Valdrics SaaS.

### Can I run it for my clients?

You can deploy or support a customer-owned or customer-controlled instance for
that customer's internal use. You cannot operate a shared hosted Valdrics
service for third-party consumption under the default repository license.

### Can I buy rights to run Valdrics as a managed service?

Yes. We provide commercial exceptions for qualified partners and OEM use cases.
See `COMMERCIAL_LICENSE.md`. Current contact path:
`licensing@valdrics.com`. Commercial evaluation requests can still flow through
`enterprise@valdrics.com`.

### Can I resell or white-label it as a hosted platform?

Not under the default BUSL/BSL terms before the change date. This requires a
separate commercial agreement.

### When does it become Apache 2.0?

On January 5, 2030, per the change terms in `LICENSE`.

### Does Apache conversion stop Valdrics-AI from making money?

No. Valdrics-AI can continue monetizing through the official SaaS, enterprise
features, support, compliance packaging, and commercial agreements.

## Related Policy Documents

- [`LICENSE`](../LICENSE)
- [`COMMERCIAL_LICENSE.md`](../COMMERCIAL_LICENSE.md)
- [`TRADEMARK_POLICY.md`](../TRADEMARK_POLICY.md)
- [`CLA.md`](../CLA.md)
