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

describe('ops page close workflow and defaults interactions', () => {
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

	it('disables run checks when no acceptance channel is selected', async () => {
		render(Page, {
			data: testOpsPageData
		});

		await screen.findByText('Integration Acceptance Runs');
		await fireEvent.click(screen.getByLabelText('Include Slack checks'));
		await fireEvent.click(screen.getByLabelText('Include Jira checks'));
		await fireEvent.click(screen.getByLabelText('Include Workflow checks'));

		const runButton = screen.getByRole('button', { name: 'Run Checks' });
		expect(runButton.hasAttribute('disabled')).toBe(true);
	});

	it('exports acceptance kpi csv', async () => {
		render(Page, {
			data: testOpsPageData
		});

		await screen.findByText('Acceptance KPI Evidence');
		await fireEvent.click(screen.getByRole('button', { name: 'Download CSV' }));

		await waitFor(() => {
			expect(
				getMock.mock.calls.some(
					(call) =>
						String(call[0]).includes('/costs/acceptance/kpis?') &&
						String(call[0]).includes('response_format=csv')
				)
			).toBe(true);
		});
		expect(createObjectUrlSpy).toHaveBeenCalled();
	});

	it('refreshes reconciliation close package with selected provider', async () => {
		render(Page, {
			data: testOpsPageData
		});

		await screen.findByText('Reconciliation Close Workflow');
		const closeCard = screen
			.getByText('Reconciliation Close Workflow')
			.closest('.card') as HTMLElement;
		const closeCardUtils = within(closeCard);
		await fireEvent.change(closeCardUtils.getByLabelText('Provider'), { target: { value: 'aws' } });
		await fireEvent.click(closeCardUtils.getByRole('button', { name: 'Preview Close Status' }));

		await waitFor(() => {
			expect(
				getMock.mock.calls.some(
					(call) =>
						String(call[0]).includes('/costs/reconciliation/close-package?') &&
						String(call[0]).includes('provider=aws') &&
						String(call[0]).includes('response_format=json')
				)
			).toBe(true);
		});
		expect(await closeCardUtils.findByText(/^READY$/)).toBeTruthy();
	});

	it('saves a provider invoice from the close workflow card', async () => {
		setupOpsGetMocks({
			closePackage: {
				tenant_id: 'tenant-id',
				provider: 'aws',
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
				invoice_reconciliation: {
					status: 'missing_invoice',
					provider: 'aws',
					period: { start_date: '2026-01-01', end_date: '2026-01-31' },
					threshold_percent: 1,
					ledger_final_cost_usd: 1200
				},
				integrity_hash: 'abc123hash',
				package_version: 'reconciliation-v3'
			}
		});
		postMock.mockResolvedValueOnce(jsonResponse({ status: 'success', invoice: { id: 'inv-1' } }));

		render(Page, {
			data: testOpsPageData
		});

		await screen.findByText('Reconciliation Close Workflow');
		const closeCard = screen
			.getByText('Reconciliation Close Workflow')
			.closest('.card') as HTMLElement;
		const closeCardUtils = within(closeCard);
		await fireEvent.input(closeCardUtils.getByLabelText('Start'), {
			target: { value: '2026-01-01' }
		});
		await fireEvent.input(closeCardUtils.getByLabelText('End'), {
			target: { value: '2026-01-31' }
		});
		await fireEvent.change(closeCardUtils.getByLabelText('Provider'), { target: { value: 'aws' } });
		await fireEvent.click(closeCardUtils.getByRole('button', { name: 'Preview Close Status' }));

		await screen.findByText('Invoice Reconciliation');
		await fireEvent.click(screen.getByRole('button', { name: 'Save Invoice' }));

		await waitFor(() => {
			expect(
				postMock.mock.calls.some((call) =>
					String(call[0]).includes('/costs/reconciliation/invoices')
				)
			).toBe(true);
		});
		const [url, body] = postMock.mock.calls.find((call) =>
			String(call[0]).includes('/costs/reconciliation/invoices')
		)!;
		expect(String(url)).toContain('/costs/reconciliation/invoices');
		expect(body).toMatchObject({
			provider: 'aws',
			start_date: '2026-01-01',
			end_date: '2026-01-31',
			currency: 'USD',
			total_amount: 1200,
			status: 'submitted'
		});
	});

	it('downloads close and restatement csv artifacts', async () => {
		render(Page, {
			data: testOpsPageData
		});

		await screen.findByText('Reconciliation Close Workflow');
		await fireEvent.click(screen.getByRole('button', { name: 'Download Close CSV' }));
		await fireEvent.click(screen.getByRole('button', { name: 'Download Restatements CSV' }));

		await waitFor(() => {
			expect(
				getMock.mock.calls.some(
					(call) =>
						String(call[0]).includes('/costs/reconciliation/close-package?') &&
						String(call[0]).includes('response_format=csv')
				)
			).toBe(true);
			expect(
				getMock.mock.calls.some(
					(call) =>
						String(call[0]).includes('/costs/reconciliation/restatements?') &&
						String(call[0]).includes('response_format=csv')
				)
			).toBe(true);
		});
		expect(createObjectUrlSpy).toHaveBeenCalled();
	});

	it('submits default volume settings through the unit economics settings API', async () => {
		render(Page, {
			data: testOpsPageData
		});

		await screen.findByText('Default Unit Volumes');
		await fireEvent.click(screen.getByRole('button', { name: 'Save Defaults' }));

		await waitFor(() => {
			expect(putMock).toHaveBeenCalledTimes(1);
		});

		const [url, body] = putMock.mock.calls[0];
		expect(String(url)).toContain('/costs/unit-economics/settings');
		expect(body).toMatchObject({
			default_request_volume: 1000,
			default_workload_volume: 200,
			default_customer_volume: 50,
			anomaly_threshold_percent: 20
		});
	});
});
