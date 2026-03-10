import { cleanup, render, screen } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';

import HealthDashboardPanel from './HealthDashboardPanel.svelte';

describe('HealthDashboardPanel', () => {
	afterEach(() => {
		cleanup();
	});

	it('renders landing funnel health metrics and alerts for internal operations users', () => {
		render(HealthDashboardPanel, {
			props: {
				dashboard: {
					generated_at: '2026-03-10T08:00:00.000Z',
					system: {
						status: 'healthy',
						uptime_hours: 42,
						last_check: '2026-03-10T08:00:00.000Z'
					},
					tenants: {
						total_tenants: 12,
						active_last_24h: 5,
						active_last_7d: 8,
						free_tenants: 4,
						paid_tenants: 8,
						churn_risk: 1
					},
					job_queue: {
						pending_jobs: 2,
						running_jobs: 1,
						failed_last_24h: 0,
						dead_letter_count: 0,
						avg_processing_time_ms: 100,
						p50_processing_time_ms: 80,
						p95_processing_time_ms: 140,
						p99_processing_time_ms: 200
					},
					llm_usage: {
						total_requests_24h: 100,
						cache_hit_rate: 0.85,
						estimated_cost_24h: 12.5,
						budget_utilization: 32
					},
					cloud_connections: {
						total_connections: 6,
						active_connections: 5,
						inactive_connections: 1,
						errored_connections: 0,
						providers: {
							aws: { total_connections: 3, active_connections: 3, inactive_connections: 0, errored_connections: 0 },
							azure: { total_connections: 2, active_connections: 1, inactive_connections: 1, errored_connections: 0 },
							gcp: { total_connections: 1, active_connections: 1, inactive_connections: 0, errored_connections: 0 }
						}
					},
					cloud_plus_connections: {
						total_connections: 4,
						active_connections: 3,
						inactive_connections: 1,
						errored_connections: 1,
						providers: {
							saas: { total_connections: 1, active_connections: 1, inactive_connections: 0, errored_connections: 0 },
							license: { total_connections: 1, active_connections: 1, inactive_connections: 0, errored_connections: 0 },
							platform: { total_connections: 1, active_connections: 0, inactive_connections: 1, errored_connections: 1 },
							hybrid: { total_connections: 1, active_connections: 1, inactive_connections: 0, errored_connections: 0 }
						}
					},
					license_governance: {
						window_hours: 24,
						active_license_connections: 2,
						requests_created_24h: 8,
						requests_completed_24h: 6,
						requests_failed_24h: 1,
						requests_in_flight: 1,
						completion_rate_percent: 75,
						failure_rate_percent: 12.5,
						avg_time_to_complete_hours: 4.2
					},
					landing_funnel: {
						weekly_current: {
							total_events: 40,
							cta_events: 14,
							signup_intent_events: 6,
							onboarded_tenants: 5,
							connected_tenants: 2,
							first_value_tenants: 1,
							pql_tenants: 1,
							pricing_view_tenants: 2,
							checkout_started_tenants: 1,
							paid_tenants: 1,
							signup_to_connection_rate: 0.4,
							connection_to_first_value_rate: 0.5
						},
						weekly_previous: {
							total_events: 32,
							cta_events: 12,
							signup_intent_events: 5,
							onboarded_tenants: 4,
							connected_tenants: 3,
							first_value_tenants: 2,
							pql_tenants: 2,
							pricing_view_tenants: 2,
							checkout_started_tenants: 1,
							paid_tenants: 0,
							signup_to_connection_rate: 0.75,
							connection_to_first_value_rate: 2 / 3
						},
						weekly_delta: {
							total_events: 8,
							signup_intent_events: 1,
							onboarded_tenants: 1,
							connected_tenants: -1,
							first_value_tenants: -1,
							pql_tenants: -1,
							pricing_view_tenants: 0,
							checkout_started_tenants: 0,
							paid_tenants: 1,
							signup_to_connection_rate: -0.35,
							connection_to_first_value_rate: -0.1667
						},
						alerts: [
							{
								key: 'signup_to_connection',
								label: 'Signup -> connection',
								status: 'watch',
								threshold_rate: 0.35,
								current_rate: 0.4,
								previous_rate: 0.75,
								weekly_delta: -0.35,
								current_numerator: 2,
								current_denominator: 5,
								message:
									'Conversion stayed above floor but deteriorated sharply versus the prior week.'
							}
						]
					}
				},
				fairUse: null,
				fairUseError: '',
				refreshing: false,
				onRefresh: vi.fn()
			}
		});

		expect(screen.getByText(/landing funnel health/i)).toBeTruthy();
		expect(screen.getByText(/7d signup → connection/i)).toBeTruthy();
		expect(screen.getByText(/floor 35.0%/i)).toBeTruthy();
		expect(screen.getByText(/conversion stayed above floor/i)).toBeTruthy();
		expect(screen.getByText(/2\/5 tenants in the current week/i)).toBeTruthy();
	});
});
