import { vi } from 'vitest';
import type { PageData } from './$types';

const hoistedMocks = vi.hoisted(() => ({
	getMock: vi.fn(),
	postMock: vi.fn(),
	putMock: vi.fn(),
	deleteMock: vi.fn()
}));
export const getMock = hoistedMocks.getMock;
export const postMock = hoistedMocks.postMock;
export const putMock = hoistedMocks.putMock;
export const deleteMock = hoistedMocks.deleteMock;

vi.mock('$env/static/public', () => ({
	PUBLIC_API_URL: 'https://api.test/api/v1'
}));

vi.mock('$env/dynamic/public', () => ({
	env: {
		PUBLIC_API_URL: 'https://api.test/api/v1'
	}
}));

vi.mock('$lib/api', () => ({
	api: {
		get: (...args: unknown[]) => getMock(...args),
		post: (...args: unknown[]) => postMock(...args),
		put: (...args: unknown[]) => putMock(...args),
		delete: (...args: unknown[]) => deleteMock(...args)
	}
}));

export function jsonResponse(payload: unknown, status = 200): Response {
	return new Response(JSON.stringify(payload), {
		status,
		headers: { 'Content-Type': 'application/json' }
	});
}

export function setupOpsGetMocks({
	requests = [],
	closePackage,
	policyPreview = {
		decision: 'allow',
		summary: 'Allowed by policy',
		tier: 'pro',
		rule_hits: []
	}
}: {
	requests?: Array<Record<string, unknown>>;
	closePackage?: Record<string, unknown>;
	policyPreview?: Record<string, unknown>;
} = {}) {
	getMock.mockImplementation(async (url: string) => {
		if (url.includes('/zombies/pending')) return jsonResponse({ requests });
		if (url.includes('/zombies/policy-preview/')) return jsonResponse(policyPreview);
		if (url.includes('/jobs/status')) {
			return jsonResponse({ pending: 0, running: 0, completed: 0, failed: 0, dead_letter: 0 });
		}
		if (url.includes('/jobs/slo?')) {
			return jsonResponse({
				window_hours: 168,
				target_success_rate_percent: 95,
				overall_meets_slo: true,
				metrics: [
					{
						job_type: 'cost_ingestion',
						window_hours: 168,
						target_success_rate_percent: 95,
						total_jobs: 5,
						successful_jobs: 5,
						failed_jobs: 0,
						success_rate_percent: 100,
						meets_slo: true,
						latest_completed_at: '2026-02-12T10:00:00Z',
						avg_duration_seconds: 120,
						p95_duration_seconds: 180
					}
				]
			});
		}
		if (url.includes('/jobs/list')) return jsonResponse([]);
		if (url.includes('/strategies/recommendations')) return jsonResponse([]);
		if (url.includes('/costs/ingestion/sla?')) {
			return jsonResponse({
				window_hours: 24,
				target_success_rate_percent: 95,
				total_jobs: 3,
				successful_jobs: 2,
				failed_jobs: 1,
				success_rate_percent: 66.67,
				meets_sla: false,
				latest_completed_at: '2026-02-12T10:00:00Z',
				avg_duration_seconds: 160,
				p95_duration_seconds: 300,
				records_ingested: 160
			});
		}
		if (url.includes('/costs/acceptance/kpis?') && url.includes('response_format=csv')) {
			return new Response('section,key,value\nmetric,test,ok\n', {
				status: 200,
				headers: {
					'Content-Type': 'text/csv',
					'Content-Disposition': 'attachment; filename="acceptance-kpis-test.csv"'
				}
			});
		}
		if (url.includes('/costs/acceptance/kpis/evidence?')) {
			return jsonResponse({ total: 0, items: [] });
		}
		if (url.includes('/costs/acceptance/kpis?')) {
			return jsonResponse({
				start_date: '2026-01-01',
				end_date: '2026-01-31',
				tier: 'pro',
				all_targets_met: false,
				available_metrics: 3,
				metrics: [
					{
						key: 'ingestion_reliability',
						label: 'Ingestion Reliability + Recency',
						available: true,
						target: '>=95.00% success and 0 stale active connections (>48h)',
						actual: '66.67% success, stale/never 1/3',
						meets_target: false,
						details: {}
					},
					{
						key: 'chargeback_coverage',
						label: 'Chargeback Allocation Coverage',
						available: true,
						target: '>=90.00%',
						actual: '92.00%',
						meets_target: true,
						details: {}
					},
					{
						key: 'unit_economics_stability',
						label: 'Unit Economics Stability',
						available: true,
						target: '<= 0 anomalous metrics',
						actual: '1 anomalous metrics',
						meets_target: false,
						details: {}
					}
				]
			});
		}
		if (url.includes('/settings/notifications/acceptance-evidence?')) {
			return jsonResponse({
				total: 4,
				items: [
					{
						event_id: 'evt-suite',
						run_id: 'run-acceptance-001',
						event_type: 'integration_test.suite',
						channel: 'suite',
						success: false,
						status_code: 207,
						message: 'Acceptance suite completed (2 passed, 1 failed).',
						actor_email: 'admin@test-ops.com',
						event_timestamp: '2026-02-12T11:00:00Z',
						details: {
							overall_status: 'partial_failure',
							passed: 2,
							failed: 1,
							checked_channels: ['slack', 'jira', 'workflow']
						}
					},
					{
						event_id: 'evt-slack',
						run_id: 'run-acceptance-001',
						event_type: 'integration_test.slack',
						channel: 'slack',
						success: true,
						status_code: 200,
						message: 'Slack notification sent successfully.',
						actor_email: 'admin@test-ops.com',
						event_timestamp: '2026-02-12T10:59:10Z',
						details: {}
					},
					{
						event_id: 'evt-jira',
						run_id: 'run-acceptance-001',
						event_type: 'integration_test.jira',
						channel: 'jira',
						success: false,
						status_code: 400,
						message: 'Jira integration not configured.',
						actor_email: 'admin@test-ops.com',
						event_timestamp: '2026-02-12T10:59:20Z',
						details: {}
					},
					{
						event_id: 'evt-workflow',
						run_id: 'run-acceptance-001',
						event_type: 'integration_test.workflow',
						channel: 'workflow',
						success: true,
						status_code: 200,
						message: 'Workflow dispatch succeeded.',
						actor_email: 'admin@test-ops.com',
						event_timestamp: '2026-02-12T10:59:30Z',
						details: {}
					}
				]
			});
		}
		if (
			url.includes('/costs/reconciliation/close-package?') &&
			url.includes('response_format=csv')
		) {
			return new Response('section,key,value\nmeta,tenant_id,test\n', {
				status: 200,
				headers: {
					'Content-Type': 'text/csv',
					'Content-Disposition': 'attachment; filename="close-package-test.csv"'
				}
			});
		}
		if (url.includes('/costs/reconciliation/close-package?')) {
			return jsonResponse(
				closePackage ?? {
					tenant_id: 'tenant-id',
					provider: 'all',
					period: { start_date: '2026-01-01', end_date: '2026-01-31' },
					close_status: 'ready',
					lifecycle: {
						total_records: 120,
						preliminary_records: 0,
						final_records: 120,
						total_cost_usd: 1200,
						preliminary_cost_usd: 0,
						final_cost_usd: 1200
					},
					reconciliation: {
						status: 'healthy',
						discrepancy_percentage: 0.42,
						confidence: 0.92
					},
					restatements: {
						count: 2,
						net_delta_usd: -4.2,
						absolute_delta_usd: 8.1
					},
					integrity_hash: 'abc123hash',
					package_version: 'reconciliation-v2'
				}
			);
		}
		if (
			url.includes('/costs/reconciliation/restatements?') &&
			url.includes('response_format=csv')
		) {
			return new Response('usage_date,recorded_at,service\n2026-01-01,2026-02-01,Zendesk\n', {
				status: 200,
				headers: {
					'Content-Type': 'text/csv',
					'Content-Disposition': 'attachment; filename="restatements-test.csv"'
				}
			});
		}
		if (url.includes('/costs/unit-economics/settings')) {
			return jsonResponse({
				id: 'd8a24b36-7b94-4a5f-9bd4-774ea239e3af',
				default_request_volume: 1000,
				default_workload_volume: 200,
				default_customer_volume: 50,
				anomaly_threshold_percent: 20
			});
		}
		if (url.includes('/costs/unit-economics?')) {
			return jsonResponse({
				start_date: '2026-01-01',
				end_date: '2026-01-31',
				total_cost: 1000,
				baseline_total_cost: 800,
				threshold_percent: 20,
				anomaly_count: 1,
				alert_dispatched: false,
				metrics: [
					{
						metric_key: 'cost_per_request',
						label: 'Cost Per Request',
						denominator: 1000,
						total_cost: 1000,
						cost_per_unit: 1,
						baseline_cost_per_unit: 0.8,
						delta_percent: 25,
						is_anomalous: true
					}
				]
			});
		}
		return jsonResponse({}, 404);
	});
}

export const testOpsPageData = {
	user: { id: 'user-id' },
	session: { access_token: 'token' },
	subscription: { tier: 'pro', status: 'active' }
} as unknown as PageData;
