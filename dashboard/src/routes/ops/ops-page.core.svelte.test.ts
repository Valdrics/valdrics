import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import {
	getMock,
	jsonResponse,
	postMock,
	putMock,
	setupOpsGetMocks,
	testOpsPageData
} from './ops-page.test.setup';
import Page from './+page.svelte';
import './ops-page.core.close_workflow.svelte.test';

describe('ops page unit economics interactions', () => {
	let createObjectUrlSpy: ReturnType<typeof vi.spyOn>;
	let revokeObjectUrlSpy: ReturnType<typeof vi.spyOn>;
	let anchorClickSpy: ReturnType<typeof vi.spyOn>;

	beforeEach(() => {
		getMock.mockReset();
		postMock.mockReset();
		putMock.mockReset();
		createObjectUrlSpy = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test');
		revokeObjectUrlSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
		anchorClickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
		setupOpsGetMocks();
		putMock.mockResolvedValue(
			jsonResponse({
				id: 'd8a24b36-7b94-4a5f-9bd4-774ea239e3af',
				default_request_volume: 1500,
				default_workload_volume: 300,
				default_customer_volume: 70,
				anomaly_threshold_percent: 25
			})
		);
	});

	afterEach(() => {
		createObjectUrlSpy.mockRestore();
		revokeObjectUrlSpy.mockRestore();
		anchorClickSpy.mockRestore();
		cleanup();
	});

	it('refreshes unit economics using the selected date window', async () => {
		render(Page, {
			data: testOpsPageData
		});

		await screen.findByText('Unit Economics Monitor');

		const unitCard = screen.getByText('Unit Economics Monitor').closest('.card') as HTMLElement;
		const dateInputs = Array.from(
			unitCard.querySelectorAll('input[type="date"]')
		) as HTMLInputElement[];
		expect(dateInputs.length).toBe(2);
		await fireEvent.input(dateInputs[0], { target: { value: '2026-02-01' } });
		await fireEvent.input(dateInputs[1], { target: { value: '2026-02-28' } });

		await fireEvent.click(screen.getByRole('button', { name: 'Refresh Unit Metrics' }));

		await waitFor(() => {
			expect(
				getMock.mock.calls.some(
					(call) =>
						String(call[0]).includes('/costs/unit-economics?') &&
						String(call[0]).includes('start_date=2026-02-01') &&
						String(call[0]).includes('end_date=2026-02-28')
				)
			).toBe(true);
		});
	});

	it('refreshes ingestion SLA using selected window', async () => {
		render(Page, {
			data: testOpsPageData
		});

		await screen.findByText('Cost Ingestion SLA');
		await screen.findByText('SLA At Risk');

		await fireEvent.change(screen.getByLabelText('SLA Window'), { target: { value: '168' } });
		await fireEvent.click(screen.getByRole('button', { name: 'Refresh SLA' }));

		await waitFor(() => {
			expect(
				getMock.mock.calls.some(
					(call) =>
						String(call[0]).includes('/costs/ingestion/sla?') &&
						String(call[0]).includes('window_hours=168') &&
						String(call[0]).includes('target_success_rate_percent=95')
				)
			).toBe(true);
		});
	});

	it('loads and refreshes job SLO using selected window', async () => {
		render(Page, {
			data: testOpsPageData
		});

		await screen.findByText('Job Reliability SLO');
		await screen.findByText('SLO Healthy');
		await screen.findByText('cost_ingestion');

		await fireEvent.change(screen.getByLabelText('Job SLO Window'), { target: { value: '72' } });
		await fireEvent.click(screen.getByRole('button', { name: 'Refresh SLO' }));

		await waitFor(() => {
			expect(
				getMock.mock.calls.some(
					(call) =>
						String(call[0]).includes('/jobs/slo?') &&
						String(call[0]).includes('window_hours=72') &&
						String(call[0]).includes('target_success_rate_percent=95')
				)
			).toBe(true);
		});
	});

	it('refreshes acceptance kpis using selected windows', async () => {
		render(Page, {
			data: testOpsPageData
		});

		await screen.findByText('Acceptance KPI Evidence');
		await screen.findByText('Gaps Open');

		const unitCard = screen.getByText('Unit Economics Monitor').closest('.card') as HTMLElement;
		const dateInputs = Array.from(
			unitCard.querySelectorAll('input[type="date"]')
		) as HTMLInputElement[];
		expect(dateInputs.length).toBe(2);
		await fireEvent.input(dateInputs[0], { target: { value: '2026-02-01' } });
		await fireEvent.input(dateInputs[1], { target: { value: '2026-02-28' } });
		await fireEvent.change(screen.getByLabelText('SLA Window'), { target: { value: '168' } });

		await fireEvent.click(screen.getByRole('button', { name: 'Refresh KPI Evidence' }));

		await waitFor(() => {
			expect(
				getMock.mock.calls.some(
					(call) =>
						String(call[0]).includes('/costs/acceptance/kpis?') &&
						String(call[0]).includes('start_date=2026-02-01') &&
						String(call[0]).includes('end_date=2026-02-28') &&
						String(call[0]).includes('ingestion_window_hours=168')
				)
			).toBe(true);
		});
	});

	it('loads and refreshes integration acceptance run evidence', async () => {
		render(Page, {
			data: testOpsPageData
		});

		await screen.findByText('Integration Acceptance Runs');
		await screen.findByText('PARTIAL FAILURE');
		expect(screen.getByText('2 passed / 1 failed')).toBeTruthy();
		expect(screen.getByText('slack: OK')).toBeTruthy();
		expect(screen.getByText('jira: FAIL')).toBeTruthy();

		await fireEvent.click(screen.getByRole('button', { name: 'Refresh Runs' }));

		await waitFor(() => {
			expect(
				getMock.mock.calls.some((call) =>
					String(call[0]).includes('/settings/notifications/acceptance-evidence?')
				)
			).toBe(true);
		});
	});

	it('captures integration acceptance run from ops and refreshes evidence', async () => {
		postMock.mockImplementation(async (url: string) => {
			if (url.includes('/settings/notifications/acceptance-evidence/capture')) {
				return jsonResponse({
					run_id: 'run-acceptance-xyz12345',
					tenant_id: 'tenant-id',
					captured_at: '2026-02-12T12:00:00Z',
					overall_status: 'success',
					passed: 3,
					failed: 0,
					results: []
				});
			}
			return jsonResponse({}, 404);
		});

		render(Page, {
			data: testOpsPageData
		});

		await screen.findByText('Integration Acceptance Runs');
		await fireEvent.click(screen.getByRole('button', { name: 'Run Checks' }));

		await waitFor(() => {
			expect(
				postMock.mock.calls.some((call) =>
					String(call[0]).includes('/settings/notifications/acceptance-evidence/capture')
				)
			).toBe(true);
		});
		expect(postMock.mock.calls[0]?.[1]).toMatchObject({
			include_slack: true,
			include_jira: true,
			include_workflow: true,
			fail_fast: false
		});

		await waitFor(() => {
			expect(
				getMock.mock.calls.filter((call) =>
					String(call[0]).includes('/settings/notifications/acceptance-evidence?')
				).length
			).toBeGreaterThan(1);
		});
		expect(await screen.findByText(/Integration acceptance run captured/i)).toBeTruthy();
	});

	it('captures acceptance run with selected channels and fail-fast options', async () => {
		postMock.mockImplementation(async (url: string) => {
			if (url.includes('/settings/notifications/acceptance-evidence/capture')) {
				return jsonResponse({
					run_id: 'run-acceptance-custom001',
					tenant_id: 'tenant-id',
					captured_at: '2026-02-12T12:10:00Z',
					overall_status: 'partial_failure',
					passed: 1,
					failed: 1,
					results: []
				});
			}
			return jsonResponse({}, 404);
		});

		render(Page, {
			data: testOpsPageData
		});

		await screen.findByText('Integration Acceptance Runs');
		await fireEvent.click(screen.getByLabelText('Include Jira checks'));
		await fireEvent.click(screen.getByLabelText('Fail fast checks'));
		await fireEvent.click(screen.getByRole('button', { name: 'Run Checks' }));

		await waitFor(() => {
			expect(
				postMock.mock.calls.some((call) =>
					String(call[0]).includes('/settings/notifications/acceptance-evidence/capture')
				)
			).toBe(true);
		});
		expect(postMock.mock.calls[0]?.[1]).toMatchObject({
			include_slack: true,
			include_jira: false,
			include_workflow: true,
			fail_fast: true
		});
		expect(await screen.findByText(/Last run run-acce/i)).toBeTruthy();
	});
});
