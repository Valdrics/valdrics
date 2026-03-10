import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, screen, waitFor } from '@testing-library/svelte';

import {
	endpoint,
	getMock,
	invalidateAllMock,
	jsonResponse,
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

	it('shows Growth as the Slack and Jira floor while keeping Pro automation integrations separate', async () => {
		setupApiMocks({
			getOverrides: {
				[endpoint('/settings/notifications')]: jsonResponse({
					slack_enabled: false,
					slack_channel_override: '',
					jira_enabled: false,
					jira_base_url: '',
					jira_email: '',
					jira_project_key: '',
					jira_issue_type: 'Task',
					has_jira_api_token: false,
					teams_enabled: false,
					teams_webhook_url: '',
					has_teams_webhook_url: false,
					workflow_github_enabled: false,
					workflow_github_owner: '',
					workflow_github_repo: '',
					workflow_github_workflow_id: '',
					workflow_github_ref: 'main',
					workflow_has_github_token: false,
					workflow_gitlab_enabled: false,
					workflow_gitlab_base_url: 'https://gitlab.com',
					workflow_gitlab_project_id: '',
					workflow_gitlab_ref: 'main',
					workflow_has_gitlab_trigger_token: false,
					workflow_webhook_enabled: false,
					workflow_webhook_url: '',
					workflow_has_webhook_bearer_token: false,
					digest_schedule: 'daily',
					digest_hour: 9,
					digest_minute: 0,
					alert_on_budget_warning: true,
					alert_on_budget_exceeded: true,
					alert_on_zombie_detected: true
				})
			}
		});
		renderPage('starter');

		await screen.findByText('Slack Notifications');

		expect(
			screen.getByText(
				/Slack delivery and Jira routing start on Growth\. Teams and workflow dispatch stay in the Pro automation lane\./i
			)
		).toBeTruthy();
		expect(screen.getAllByText('Growth Plan Required').length).toBeGreaterThan(0);
		expect(
			screen.getByText(
				/Create Jira issues from policy and remediation events on Growth and above\./i
			)
		).toBeTruthy();
		expect(
			screen.getByText(/Route policy and remediation alerts into Teams on Pro and Enterprise\./i)
		).toBeTruthy();
		expect((screen.getByLabelText('Enable Slack notifications') as HTMLInputElement).disabled).toBe(
			true
		);
		expect(
			(screen.getByRole('button', { name: /Send test Slack notification/i }) as HTMLButtonElement)
				.disabled
		).toBe(true);
	});
});
