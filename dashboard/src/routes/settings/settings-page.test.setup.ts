import { vi } from 'vitest';
import { render } from '@testing-library/svelte';

import Page from './+page.svelte';
import type { PageData } from './$types';

const hoistedMocks = vi.hoisted(() => ({
	getMock: vi.fn(),
	putMock: vi.fn(),
	postMock: vi.fn(),
	invalidateAllMock: vi.fn()
}));

export const getMock = hoistedMocks.getMock;
export const putMock = hoistedMocks.putMock;
export const postMock = hoistedMocks.postMock;
export const invalidateAllMock = hoistedMocks.invalidateAllMock;

vi.mock('$env/static/public', () => ({
	PUBLIC_API_URL: 'https://api.test/api/v1'
}));

vi.mock('$env/dynamic/public', () => ({
	env: {
		PUBLIC_API_URL: 'https://api.test/api/v1'
	}
}));

vi.mock('$app/paths', () => ({
	base: ''
}));

vi.mock('$app/navigation', () => ({
	invalidateAll: (...args: unknown[]) => invalidateAllMock(...args)
}));

vi.mock('$lib/api', () => ({
	api: {
		get: (...args: unknown[]) => getMock(...args),
		put: (...args: unknown[]) => putMock(...args),
		post: (...args: unknown[]) => postMock(...args)
	}
}));

export function jsonResponse(payload: unknown, status = 200): Response {
	return new Response(JSON.stringify(payload), {
		status,
		headers: { 'Content-Type': 'application/json' }
	});
}

const EDGE_BASE = '/api/edge/api/v1';
export const endpoint = (path: string): string => `${EDGE_BASE}${path}`;
export const directApiEndpoint = (path: string): string => `https://api.test/api/v1${path}`;

export function baseSettingsData(tier: string = 'enterprise'): PageData {
	return {
		user: { id: 'user-id', tenant_id: 'tenant-id' },
		session: { access_token: 'token' },
		subscription: { tier, status: 'active' },
		profile: { persona: 'engineering' }
	} as unknown as PageData;
}

export function setupApiMocks({
	getOverrides = {},
	putOverrides = {},
	postOverrides = {}
}: {
	getOverrides?: Record<string, Response>;
	putOverrides?: Record<string, Response>;
	postOverrides?: Record<string, Response>;
} = {}) {
	const getDefaults: Record<string, Response> = {
		[endpoint('/settings/notifications')]: jsonResponse({
			slack_enabled: true,
			slack_channel_override: 'C02468',
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
		}),
		[endpoint('/settings/carbon')]: jsonResponse({
			carbon_budget_kg: 220,
			alert_threshold_percent: 80,
			default_region: 'us-west-2',
			email_enabled: true,
			email_recipients: 'ops@valdrics.test'
		}),
		[endpoint('/settings/llm/models')]: jsonResponse({
			groq: ['llama-3.3-70b-versatile'],
			openai: ['gpt-4.1'],
			anthropic: ['claude-3-5-sonnet'],
			google: ['gemini-2.5-pro']
		}),
		[endpoint('/settings/llm')]: jsonResponse({
			monthly_limit_usd: 15,
			alert_threshold_percent: 85,
			hard_limit: false,
			preferred_provider: 'groq',
			preferred_model: 'llama-3.3-70b-versatile',
			openai_api_key: '',
			claude_api_key: '',
			google_api_key: '',
			groq_api_key: '',
			has_openai_key: false,
			has_claude_key: false,
			has_google_key: false,
			has_groq_key: false
		}),
		[endpoint('/settings/activeops')]: jsonResponse({
			auto_pilot_enabled: true,
			min_confidence_threshold: 0.95,
			policy_enabled: true,
			policy_block_production_destructive: true,
			policy_require_gpu_override: true,
			policy_low_confidence_warn_threshold: 0.9,
			policy_violation_notify_slack: true,
			policy_violation_notify_jira: false,
			policy_escalation_required_role: 'owner',
			license_auto_reclaim_enabled: true,
			license_inactive_threshold_days: 30,
			license_reclaim_grace_period_days: 3,
			license_downgrade_recommendations_enabled: true
		}),
		[endpoint('/settings/safety')]: jsonResponse({
			circuit_state: 'closed',
			failure_count: 1,
			daily_savings_used: 25,
			daily_savings_limit: 500,
			last_failure_at: null,
			can_execute: true
		}),
		[endpoint('/settings/identity')]: jsonResponse({
			sso_enabled: false,
			allowed_email_domains: [],
			sso_federation_enabled: false,
			sso_federation_mode: 'domain',
			sso_federation_provider_id: null,
			scim_enabled: false,
			has_scim_token: false,
			scim_last_rotated_at: null
		}),
		[directApiEndpoint('/settings/identity')]: jsonResponse({
			sso_enabled: false,
			allowed_email_domains: [],
			sso_federation_enabled: false,
			sso_federation_mode: 'domain',
			sso_federation_provider_id: null,
			scim_enabled: false,
			has_scim_token: false,
			scim_last_rotated_at: null
		}),
		[endpoint('/settings/identity/diagnostics')]: jsonResponse({
			tier: 'enterprise',
			sso: {
				enabled: false,
				allowed_email_domains: [],
				enforcement_active: false,
				federation_enabled: false,
				federation_mode: 'domain',
				federation_ready: false,
				current_admin_domain: 'valdrics.test',
				current_admin_domain_allowed: true,
				issues: []
			},
			scim: {
				available: true,
				enabled: false,
				has_token: false,
				token_blind_index_present: false,
				last_rotated_at: null,
				token_age_days: null,
				rotation_recommended_days: 90,
				rotation_overdue: false,
				issues: []
			},
			recommendations: []
		}),
		[directApiEndpoint('/settings/identity/diagnostics')]: jsonResponse({
			tier: 'enterprise',
			sso: {
				enabled: false,
				allowed_email_domains: [],
				enforcement_active: false,
				federation_enabled: false,
				federation_mode: 'domain',
				federation_ready: false,
				current_admin_domain: 'valdrics.test',
				current_admin_domain_allowed: true,
				issues: []
			},
			scim: {
				available: true,
				enabled: false,
				has_token: false,
				token_blind_index_present: false,
				last_rotated_at: null,
				token_age_days: null,
				rotation_recommended_days: 90,
				rotation_overdue: false,
				issues: []
			},
			recommendations: []
		}),
		[endpoint('/settings/notifications/policy-diagnostics')]: jsonResponse({
			tier: 'enterprise',
			has_activeops_settings: true,
			has_notification_settings: true,
			policy_enabled: true,
			slack: {
				enabled_for_policy: true,
				enabled_in_notifications: true,
				ready: true,
				reasons: [],
				has_bot_token: true,
				has_default_channel: true,
				has_channel_override: false,
				selected_channel: null,
				channel_source: 'default'
			},
			jira: {
				enabled_for_policy: false,
				enabled_in_notifications: false,
				ready: false,
				reasons: ['jira_disabled'],
				feature_allowed_by_tier: true,
				has_base_url: false,
				has_email: false,
				has_project_key: false,
				has_api_token: false,
				issue_type: 'Task'
			}
		})
	};

	const putDefaults: Record<string, Response> = {
		[endpoint('/settings/profile')]: jsonResponse({ persona: 'finance' }),
		[endpoint('/settings/notifications')]: jsonResponse({ status: 'ok' }),
		[endpoint('/settings/carbon')]: jsonResponse({ status: 'ok' }),
		[endpoint('/settings/llm')]: jsonResponse({
			has_openai_key: true,
			has_claude_key: false,
			has_google_key: false,
			has_groq_key: false
		}),
		[endpoint('/settings/activeops')]: jsonResponse({ status: 'ok' }),
		[endpoint('/settings/identity')]: jsonResponse({ status: 'ok' })
	};

	const postDefaults: Record<string, Response> = {
		[endpoint('/settings/notifications/test-slack')]: jsonResponse({ status: 'ok' }),
		[endpoint('/settings/notifications/test-jira')]: jsonResponse({ status: 'ok' }),
		[endpoint('/settings/notifications/test-teams')]: jsonResponse({ status: 'ok' }),
		[endpoint('/settings/notifications/test-workflow')]: jsonResponse({ status: 'ok' }),
		[endpoint('/settings/safety/reset')]: jsonResponse({ status: 'ok' })
	};

	const getMap = { ...getDefaults, ...getOverrides };
	const putMap = { ...putDefaults, ...putOverrides };
	const postMap = { ...postDefaults, ...postOverrides };

	getMock.mockImplementation(async (url: string) => getMap[String(url)] ?? jsonResponse({}, 404));
	putMock.mockImplementation(async (url: string) => putMap[String(url)] ?? jsonResponse({}, 404));
	postMock.mockImplementation(async (url: string) => postMap[String(url)] ?? jsonResponse({}, 404));
}

export function renderPage(tier: string = 'enterprise') {
	return render(Page, { data: baseSettingsData(tier) });
}
