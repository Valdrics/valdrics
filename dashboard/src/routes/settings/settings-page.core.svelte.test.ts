import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, screen, waitFor } from '@testing-library/svelte';

import {
	endpoint,
	getMock,
	invalidateAllMock,
	postMock,
	putMock,
	renderPage,
	setupApiMocks
} from './settings-page.test.setup';

describe('settings page integration wiring (core)', () => {
	beforeEach(() => {
		getMock.mockReset();
		putMock.mockReset();
		postMock.mockReset();
		invalidateAllMock.mockReset();
		setupApiMocks();
	});

	afterEach(() => {
		cleanup();
	});

	it('loads settings modules via edge-proxy contract endpoints', async () => {
		renderPage();

		await screen.findByLabelText('Slack channel ID override');

		await waitFor(() => {
			expect(getMock).toHaveBeenCalledWith(
				endpoint('/settings/notifications'),
				expect.objectContaining({ headers: expect.any(Object), timeoutMs: 8000 })
			);
			expect(getMock).toHaveBeenCalledWith(
				endpoint('/settings/carbon'),
				expect.objectContaining({ headers: expect.any(Object), timeoutMs: 8000 })
			);
			expect(getMock).toHaveBeenCalledWith(
				endpoint('/settings/llm/models'),
				expect.objectContaining({ timeoutMs: 8000 })
			);
			expect(getMock).toHaveBeenCalledWith(
				endpoint('/settings/llm'),
				expect.objectContaining({ headers: expect.any(Object), timeoutMs: 8000 })
			);
			expect(getMock).toHaveBeenCalledWith(
				endpoint('/settings/activeops'),
				expect.objectContaining({ headers: expect.any(Object), timeoutMs: 8000 })
			);
			expect(getMock).toHaveBeenCalledWith(
				endpoint('/settings/safety'),
				expect.objectContaining({ headers: expect.any(Object), timeoutMs: 8000 })
			);
		});

		await waitFor(() => {
			const channel = screen.getByLabelText('Slack channel ID override') as HTMLInputElement;
			expect(channel.value).toBe('C02468');
			const carbonBudget = screen.getByLabelText(
				'Monthly carbon budget in kilograms'
			) as HTMLInputElement;
			expect(carbonBudget.value).toBe('220');
		});
	});

	it('saves persona through profile endpoint and invalidates route data', async () => {
		renderPage();
		await screen.findByLabelText('Default persona');

		await fireEvent.change(screen.getByLabelText('Default persona'), {
			target: { value: 'finance' }
		});
		await fireEvent.click(screen.getByRole('button', { name: /Save Persona/i }));

		await waitFor(() => {
			expect(putMock).toHaveBeenCalledWith(
				endpoint('/settings/profile'),
				{ persona: 'finance' },
				expect.objectContaining({ headers: expect.any(Object) })
			);
		});
		expect(invalidateAllMock).toHaveBeenCalled();
	});

	it('writes notification settings and surfaces save errors', async () => {
		setupApiMocks({
			putOverrides: {
				[endpoint('/settings/notifications')]: new Response(
					JSON.stringify({ detail: 'Failed to save settings' }),
					{ status: 500, headers: { 'Content-Type': 'application/json' } }
				)
			}
		});
		renderPage();
		await screen.findByRole('button', { name: /Save Settings/i });

		await fireEvent.click(screen.getByRole('button', { name: /Save Settings/i }));

		await waitFor(() => {
			expect(putMock).toHaveBeenCalledWith(
				endpoint('/settings/notifications'),
				expect.objectContaining({
					digest_schedule: expect.any(String),
					alert_on_zombie_detected: expect.any(Boolean)
				}),
				expect.objectContaining({ headers: expect.any(Object) })
			);
		});
		await screen.findByText('Failed to save settings');
	});
});
