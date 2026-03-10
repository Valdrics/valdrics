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

	it('opens remediation review modal and loads policy preview', async () => {
		setupOpsGetMocks({
			requests: [
				{
					id: '7f2d7ca8-18e3-472f-9d65-ec7f0da8d0f1',
					status: 'pending',
					resource_id: 'i-gpu-node',
					resource_type: 'GPU Instance',
					action: 'terminate_instance',
					estimated_savings: 123.45,
					created_at: '2026-02-12T10:00:00Z',
					escalation_required: true,
					escalation_reason: 'Owner approval required'
				}
			],
			policyPreview: {
				decision: 'escalate',
				summary: 'High-risk action requires owner approval.',
				tier: 'pro',
				rule_hits: [{ rule_id: 'gpu_high_risk', message: 'GPU termination policy' }]
			}
		});

		render(Page, { data: testOpsPageData });
		await screen.findByText('Remediation Queue');
		const reviewButton = await screen.findByRole('button', { name: 'Review' });
		await fireEvent.click(reviewButton);

		const dialog = await screen.findByRole('dialog', { name: 'Remediation review' });
		expect(
			await within(dialog).findByText(/^High-risk action requires owner approval\.$/)
		).toBeTruthy();
		expect(await within(dialog).findByText(/^ESCALATE$/)).toBeTruthy();

		await waitFor(() => {
			expect(
				getMock.mock.calls.some((call) =>
					String(call[0]).includes('/zombies/policy-preview/7f2d7ca8-18e3-472f-9d65-ec7f0da8d0f1')
				)
			).toBe(true);
		});
	});

	it('approves a request from the remediation review modal', async () => {
		setupOpsGetMocks({
			requests: [
				{
					id: 'f11f8fa7-c2f6-4e3d-bcd8-8e7d42574512',
					status: 'pending_approval',
					resource_id: 'i-owner-review',
					resource_type: 'Instance',
					action: 'stop_instance',
					estimated_savings: 40,
					created_at: '2026-02-12T10:00:00Z'
				}
			]
		});
		postMock.mockImplementation(async (url: string) => {
			if (url.includes('/zombies/approve/')) {
				return jsonResponse({
					status: 'approved',
					request_id: 'f11f8fa7-c2f6-4e3d-bcd8-8e7d42574512'
				});
			}
			return jsonResponse({}, 404);
		});

		render(Page, { data: testOpsPageData });
		await screen.findByText('Remediation Queue');
		const reviewButton = await screen.findByRole('button', { name: 'Review' });
		await fireEvent.click(reviewButton);

		const dialog = await screen.findByRole('dialog', { name: 'Remediation review' });
		await fireEvent.click(within(dialog).getByRole('button', { name: 'Approve' }));

		await waitFor(() => {
			expect(
				postMock.mock.calls.some((call) =>
					String(call[0]).includes('/zombies/approve/f11f8fa7-c2f6-4e3d-bcd8-8e7d42574512')
				)
			).toBe(true);
		});
		expect(await within(dialog).findByText(/approved\./i)).toBeTruthy();
	});

	it('executes a request from the remediation review modal when approved', async () => {
		setupOpsGetMocks({
			requests: [
				{
					id: '8454e787-4f57-4e98-969f-d8b16a74817e',
					status: 'approved',
					resource_id: 'i-exec-ready',
					resource_type: 'Instance',
					action: 'stop_instance',
					estimated_savings: 22.5,
					created_at: '2026-02-12T10:00:00Z'
				}
			]
		});
		postMock.mockImplementation(async (url: string) => {
			if (url.includes('/zombies/execute/')) {
				return jsonResponse({
					status: 'scheduled',
					request_id: '8454e787-4f57-4e98-969f-d8b16a74817e'
				});
			}
			return jsonResponse({}, 404);
		});

		render(Page, { data: testOpsPageData });
		await screen.findByText('Remediation Queue');
		const reviewButton = await screen.findByRole('button', { name: 'Review' });
		await fireEvent.click(reviewButton);

		const dialog = await screen.findByRole('dialog', { name: 'Remediation review' });
		await fireEvent.click(within(dialog).getByRole('button', { name: 'Execute' }));

		await waitFor(() => {
			expect(
				postMock.mock.calls.some((call) =>
					String(call[0]).includes('/zombies/execute/8454e787-4f57-4e98-969f-d8b16a74817e')
				)
			).toBe(true);
		});
		expect(await within(dialog).findByText(/scheduled after grace period\./i)).toBeTruthy();
	});

	it('keeps execute disabled when request is pending approval', async () => {
		setupOpsGetMocks({
			requests: [
				{
					id: '18280f41-599e-40a1-b651-4f2f5a5f45a7',
					status: 'pending_approval',
					resource_id: 'i-awaiting-approval',
					resource_type: 'Instance',
					action: 'stop_instance',
					estimated_savings: 11,
					created_at: '2026-02-12T10:00:00Z'
				}
			]
		});

		render(Page, { data: testOpsPageData });
		await screen.findByText('Remediation Queue');
		const reviewButton = await screen.findByRole('button', { name: 'Review' });
		await fireEvent.click(reviewButton);

		const dialog = await screen.findByRole('dialog', { name: 'Remediation review' });
		const executeButton = within(dialog).getByRole('button', { name: 'Awaiting Approval' });
		expect(executeButton.hasAttribute('disabled')).toBe(true);
	});
});
