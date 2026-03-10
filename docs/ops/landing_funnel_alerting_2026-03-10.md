# Landing Funnel Alerting Contract

**Date:** 2026-03-10  
**Scope:** Internal growth and activation alerting

## Purpose

Valdrics publishes weekly landing-funnel health into Prometheus so internal
operators get proactive Alertmanager notifications instead of relying on
manual dashboard review.

## Refresh path

- Scheduler task: `scheduler.refresh_landing_funnel_health`
- Schedule: hourly at minute `10` UTC
- Inline fallback: APScheduler can run the same logic inline if Celery dispatch
  is unavailable
- Source of truth:
  - `LandingTelemetryDailyRollup`
  - `TenantGrowthFunnelSnapshot`

## Exported metrics

- `valdrics_ops_landing_funnel_weekly_conversion_rate{step=...}`
- `valdrics_ops_landing_funnel_weekly_delta_rate{step=...}`
- `valdrics_ops_landing_funnel_weekly_threshold_rate{step=...}`
- `valdrics_ops_landing_funnel_weekly_numerator{step=...}`
- `valdrics_ops_landing_funnel_weekly_denominator{step=...}`
- `valdrics_ops_landing_funnel_health_status{step=...}`
- `valdrics_ops_landing_funnel_last_evaluated_unixtime`

## Alert rules

- `LandingSignupToConnectionCritical`
- `LandingConnectionToFirstValueCritical`
- `LandingSignupToConnectionWatch`
- `LandingConnectionToFirstValueWatch`
- `LandingFunnelHealthMetricsStale`

## Operating thresholds

- Signup -> connection floor: `35%`
- Connection -> first value floor: `40%`
- Watch deterioration threshold: `-10` percentage points week over week
- Metrics stale threshold: `2 hours` since last successful refresh

## Expected internal action

1. Confirm the scheduler refreshed metrics successfully.
2. Inspect `/admin/health` and `/admin/landing-campaigns` for the affected step.
3. Determine whether degradation is caused by acquisition quality,
   onboarding friction, or first-value activation failure.
4. Treat `LandingFunnelHealthMetricsStale` as an observability incident before
   trusting funnel status.
