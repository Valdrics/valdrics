import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import RemediationModal from './RemediationModal.svelte';

const { postMock } = vi.hoisted(() => ({
	postMock: vi.fn()
}));

vi.mock('$lib/api', () => ({
	api: {
		post: postMock
	}
}));

vi.mock('$lib/edgeProxy', () => ({
	edgeApiPath: (path: string) => `/api/edge/api/v1${path}`
}));

function jsonResponse(payload: unknown, status = 200): Response {
	return new Response(JSON.stringify(payload), {
		status,
		headers: { 'Content-Type': 'application/json' }
	});
}

describe('RemediationModal', () => {
	beforeEach(() => {
		postMock.mockReset();
	});

	afterEach(() => {
		cleanup();
	});

	it('uses finding_id for policy preview and request creation', async () => {
		postMock
			.mockResolvedValueOnce(
				jsonResponse({
					decision: 'allow',
					summary: 'Safe to queue',
					tier: 'pro',
					rule_hits: []
				})
			)
			.mockResolvedValueOnce(
				jsonResponse({
					status: 'pending',
					request_id: 'req-123'
				})
			);

		render(RemediationModal, {
			isOpen: true,
			finding: {
				finding_id: 'finding-123',
				resource_id: 'i-abc123',
				resource_type: 'ec2_instance',
				provider: 'aws',
				recommended_action: 'stop',
				monthly_cost: '$22.00'
			},
			accessToken: 'token',
			onClose: vi.fn()
		});

		await waitFor(() => expect(postMock).toHaveBeenCalledTimes(1));
		expect(postMock.mock.calls[0]?.[1]).toEqual({
			finding_id: 'finding-123',
			action: 'stop_instance',
			parameters: { target_size: '' }
		});
		expect(postMock.mock.calls[0]?.[1]).not.toHaveProperty('resource_id');
		expect(postMock.mock.calls[0]?.[1]).not.toHaveProperty('provider');

		const submitButton = screen.getByRole('button', { name: 'Approve & Queue' });
		await waitFor(() => expect(submitButton.hasAttribute('disabled')).toBe(false));
		await fireEvent.click(submitButton);

		await waitFor(() => expect(postMock).toHaveBeenCalledTimes(2));
		expect(postMock.mock.calls[1]?.[1]).toEqual({
			finding_id: 'finding-123',
			action: 'stop_instance',
			create_backup: true,
			parameters: { target_size: '' }
		});
		expect(await screen.findByText(/Request req-123 created\./i)).toBeTruthy();
	});

	it('fails closed when finding_id is missing', async () => {
		render(RemediationModal, {
			isOpen: true,
			finding: {
				resource_id: 'i-abc123',
				resource_type: 'ec2_instance',
				provider: 'aws',
				recommended_action: 'stop',
				monthly_cost: '$22.00'
			},
			accessToken: 'token',
			onClose: vi.fn()
		});

		expect(
			await screen.findByText(/Persisted finding binding missing\. Rerun the scan/i)
		).toBeTruthy();
		expect(postMock).not.toHaveBeenCalled();
		const submitButton = screen.getByRole('button', { name: 'Approve & Queue' });
		expect(submitButton.hasAttribute('disabled')).toBe(true);
	});
});
