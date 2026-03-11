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

describe('settings page integration wiring (advanced)', () => {
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

	it('writes carbon, llm, and activeops settings to dedicated endpoints', async () => {
		renderPage();
		await screen.findByRole('button', { name: /Save carbon budget settings/i });

		await fireEvent.click(screen.getByRole('button', { name: /Save carbon budget settings/i }));
		await waitFor(() => {
			expect(putMock).toHaveBeenCalledWith(
				endpoint('/settings/carbon'),
				expect.objectContaining({ carbon_budget_kg: expect.any(Number) }),
				expect.objectContaining({ headers: expect.any(Object) })
			);
		});

		const openAiKey = screen.getByLabelText('OpenAI API Key') as HTMLInputElement;
		await fireEvent.input(openAiKey, { target: { value: 'sk-test-key-with-valid-length-12345' } });
		await fireEvent.click(screen.getByRole('button', { name: /Save AI Strategy/i }));
		await waitFor(() => {
			expect(putMock).toHaveBeenCalledWith(
				endpoint('/settings/llm'),
				expect.objectContaining({ preferred_provider: expect.any(String) }),
				expect.objectContaining({ headers: expect.any(Object) })
			);
		});

		await fireEvent.click(screen.getByRole('button', { name: /Save ActiveOps Settings/i }));
		await waitFor(() => {
			expect(putMock).toHaveBeenCalledWith(
				endpoint('/settings/activeops'),
				expect.objectContaining({
					auto_pilot_enabled: expect.any(Boolean),
					policy_enabled: expect.any(Boolean)
				}),
				expect.objectContaining({ headers: expect.any(Object) })
			);
		});
	});

	it('handles safety read/reset success and admin error paths', async () => {
		renderPage();
		await screen.findByRole('button', { name: /Reset remediation circuit breaker/i });

		await fireEvent.click(
			screen.getByRole('button', { name: /Reset remediation circuit breaker/i })
		);
		await waitFor(() => {
			expect(postMock).toHaveBeenCalledWith(
				endpoint('/settings/safety/reset'),
				{},
				expect.objectContaining({ headers: expect.any(Object) })
			);
		});

		setupApiMocks({
			postOverrides: {
				[endpoint('/settings/safety/reset')]: new Response('{}', { status: 403 })
			}
		});
		await fireEvent.click(
			screen.getByRole('button', { name: /Reset remediation circuit breaker/i })
		);
		await screen.findByText('Admin role required to reset the circuit breaker.');
	});

	it('handles notification test and diagnostics error paths', async () => {
		setupApiMocks({
			postOverrides: {
				[endpoint('/settings/notifications/test-slack')]: new Response(
					JSON.stringify({ detail: 'Slack integration missing' }),
					{ status: 400, headers: { 'Content-Type': 'application/json' } }
				)
			}
		});
		renderPage();
		await screen.findByRole('button', { name: /Send test Slack notification/i });

		await fireEvent.click(screen.getByRole('button', { name: /Send test Slack notification/i }));
		await waitFor(() => {
			expect(postMock).toHaveBeenCalledWith(
				endpoint('/settings/notifications/test-slack'),
				{},
				expect.objectContaining({ headers: expect.any(Object) })
			);
		});
		await screen.findByText('Slack integration missing');

		await fireEvent.click(
			screen.getByRole('button', { name: /Run policy notification diagnostics/i })
		);
		await waitFor(() => {
			expect(getMock).toHaveBeenCalledWith(
				endpoint('/settings/notifications/policy-diagnostics'),
				expect.objectContaining({ headers: expect.any(Object) })
			);
		});
	});

	it('explains that activeops automation stays on the Pro lane', async () => {
		renderPage('growth');
		await screen.findByText('ActiveOps (Autonomous Remediation)');

		expect(document.body.textContent || '').toMatch(/Move to Pro for ActiveOps automation/i);
		expect(document.body.textContent || '').toMatch(
			/ActiveOps automation stays on Pro and Enterprise\./i
		);
		expect(document.body.textContent || '').toMatch(
			/Slack and Jira switches in this card apply to\s+remediation policy events/i
		);
		expect(screen.getAllByRole('link', { name: /View Pro plan/i }).length).toBeGreaterThan(0);
	});
});
