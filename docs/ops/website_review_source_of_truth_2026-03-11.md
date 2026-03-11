# Valdrics Website Review

Date: 2026-03-11
Status: Internal source-of-truth review

## Scope

This review is based on the current public site implementation and public route surface in the repository, not on an external analyst summary.

Primary public sources reviewed:
- `/` landing page
- `/pricing`
- `/enterprise`
- `/resources`
- `/docs`
- `/proof`
- `/insights`
- `/status`
- `/about`

Primary implementation sources reviewed:
- [heroContent.core.ts](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/lib/landing/heroContent.core.ts)
- [publicPlans.ts](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/lib/pricing/publicPlans.ts)
- [LandingHero.svelte](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/lib/components/LandingHero.svelte)
- [LandingTrustSection.svelte](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/lib/components/landing/LandingTrustSection.svelte)
- [publicNav.ts](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/lib/landing/publicNav.ts)

## Product Overview

Valdrics is positioned as a governed operating layer for cloud, SaaS, and software spend. The site does not present the product as a dashboard-only cost tool. The core story is that a spend issue should move from signal, to owner, to approval, to recorded proof inside one controlled operating path.

Evidence:
- Landing hero and control-loop messaging in [heroContent.core.ts](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/lib/landing/heroContent.core.ts)
- Landing structure in [LandingHero.svelte](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/lib/components/LandingHero.svelte)
- Capabilities narrative in [LandingCapabilitiesSection.svelte](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/lib/components/landing/LandingCapabilitiesSection.svelte)

## What The Site Gets Right

### 1. The control-loop story is clear

The public site consistently explains that Valdrics is about governed action, not just visibility:
- signals are scoped
- owners are assigned
- policy and approval checks stay attached
- outcomes are recorded for review

This is the strongest part of the current positioning.

### 2. Pricing is transparent

The public ladder is explicit and self-serve:
- `Free`
- `Starter`
- `Growth`
- `Pro`
- separate enterprise diligence lane

Evidence:
- [publicPlans.ts](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/lib/pricing/publicPlans.ts)
- [pricing/+page.svelte](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/routes/pricing/+page.svelte)

### 3. Trust and diligence surfaces exist

The site already exposes public routes that technical and enterprise-adjacent buyers expect:
- docs
- API docs
- proof pack
- resources
- status
- enterprise governance page
- about page

Evidence:
- [publicNav.ts](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/lib/landing/publicNav.ts)
- [routeProtection.ts](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/lib/routeProtection.ts)
- [sitemap.xml/+server.ts](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/routes/sitemap.xml/+server.ts)

### 4. The site is honest about prelaunch state

The current public trust layer now states the proof posture directly instead of implying customer evidence that does not exist yet.

Evidence:
- [LandingTrustSection.svelte](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/lib/components/landing/LandingTrustSection.svelte)
- [about/+page.svelte](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/routes/about/+page.svelte)

## Current Pricing Surface

This is the current public package story from [publicPlans.ts](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/lib/pricing/publicPlans.ts):

### Free
- permanent free workspace
- one AWS account
- weekly zombie scans
- 30-day retention
- one guided AI analysis per day

### Starter
- up to five AWS accounts
- one Azure tenant
- one GCP project
- AI insights
- stronger alerting
- ingestion SLA monitoring
- 90-day retention

### Growth
- full AWS, Azure, and GCP coverage
- anomaly detection
- Slack
- Jira
- SSO
- chargeback
- backfill
- non-production auto-remediation

### Pro
- API access
- audit logs
- hourly scans
- reconciliation
- close workflow
- compliance exports
- Cloud+ connectors
- savings proof
- incident integrations

### Enterprise lane
- SCIM
- private deployment / custom control path
- procurement and security diligence path

## Corrections To Prior Narrative Reviews

### 1. “Detailed citations” should not be claimed unless they are actually included

Any external-facing review needs route references, page references, or direct links. A polished summary without citations is not a diligence-grade artifact.

### 2. Growth currently includes Jira

Earlier internal commentary that suggested Jira remained only in the higher automation lane is not consistent with the current package contract.

Current evidence:
- Growth feature list in [publicPlans.ts](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/lib/pricing/publicPlans.ts)
- Growth-facing settings copy in [SettingsNotificationControls.svelte](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/dashboard/src/routes/settings/SettingsNotificationControls.svelte)
- backend notification entitlement coverage in:
  - [test_notifications_teams_jira.py](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/tests/unit/governance/settings/test_notifications_teams_jira.py)
  - [test_notification_entitlement_ops.py](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/tests/unit/governance/settings/test_notification_entitlement_ops.py)

### 3. “Comprehensive connector coverage” should be phrased more carefully

The safer public claim is that Valdrics supports cloud, SaaS, and software inputs across named public integrations and buyer-facing routes. That is stronger and more defensible than broad analyst-style language.

## Where Valdrics Is Different From Traditional Cost Tools

Valdrics is trying to win on four things:
- owner-routed action instead of visibility-only reporting
- approval-aware execution instead of alert-only workflows
- one operating path across cloud, SaaS, and software instead of fragmented cost tooling
- reviewable proof that survives finance, security, and leadership review

This is the most defensible differentiation on the site today.

## Current Proof Gap

This is still the main commercial weakness.

What does not exist publicly yet:
- customer logos
- public case studies
- published ROI studies tied to named customers

What does exist publicly today:
- transparent pricing
- prelaunch-safe proof messaging
- docs, proof, and status routes
- design-partner-informed messaging
- enterprise diligence materials

This is enough for an honest prelaunch narrative, but not enough for incumbent-style trust.

## Best Use Of This Review

Good use:
- internal GTM alignment
- landing-page narrative review
- investor/advisor briefing draft
- sales messaging calibration

Not yet good use:
- external analyst report
- procurement-ready diligence memo on its own
- competitive dossier claiming category leadership

## Bottom Line

The public site now presents Valdrics as a governed spend control product rather than a generic cost dashboard. The pricing model is clearer, the route surface is more mature, and the trust copy is more honest than before. The remaining gap is not messaging architecture; it is public proof.

The next meaningful improvement is not another copy pass. It is adding real evidence:
- design-partner count, if true
- customer proof, when it exists
- implementation proof
- clearer founder/team/company credibility over time
