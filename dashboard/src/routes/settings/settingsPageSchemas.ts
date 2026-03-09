import { z } from 'zod';

export type PolicyChannelDiagnostics = {
	enabled_for_policy: boolean;
	enabled_in_notifications: boolean;
	ready: boolean;
	reasons: string[];
};

export type PolicyDiagnostics = {
	tier: string;
	has_activeops_settings: boolean;
	has_notification_settings: boolean;
	policy_enabled: boolean;
	slack: PolicyChannelDiagnostics & {
		feature_allowed_by_tier: boolean;
		has_bot_token: boolean;
		has_default_channel: boolean;
		has_channel_override: boolean;
		selected_channel?: string | null;
		channel_source: string;
	};
	jira: PolicyChannelDiagnostics & {
		feature_allowed_by_tier: boolean;
		has_base_url: boolean;
		has_email: boolean;
		has_project_key: boolean;
		has_api_token: boolean;
		issue_type: string;
	};
};

export type SafetyStatus = {
	circuit_state: string;
	failure_count: number;
	daily_savings_used: number;
	daily_savings_limit: number;
	last_failure_at: string | null;
	can_execute: boolean;
};

export function formatCircuitState(state: string): string {
	const normalized = state.replaceAll('_', ' ');
	return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

export function safetyUsagePercent(status: SafetyStatus | null): number {
	if (!status || status.daily_savings_limit <= 0) return 0;
	return Math.min((status.daily_savings_used / status.daily_savings_limit) * 100, 100);
}

export function formatSafetyDate(value: string | null): string {
	if (!value) return 'None';
	const parsed = new Date(value);
	if (Number.isNaN(parsed.getTime())) return value;
	return parsed.toLocaleString();
}

export const NotificationSettingsSchema = z.object({
	slack_enabled: z.boolean(),
	slack_channel_override: z.string().max(50).optional(),
	jira_enabled: z.boolean(),
	jira_base_url: z.string().max(255).optional(),
	jira_email: z.string().email().optional(),
	jira_project_key: z.string().max(32).optional(),
	jira_issue_type: z.string().max(64).optional(),
	jira_api_token: z.string().max(1024).optional(),
	clear_jira_api_token: z.boolean().optional(),
	teams_enabled: z.boolean(),
	teams_webhook_url: z.string().max(1024).optional(),
	clear_teams_webhook_url: z.boolean().optional(),
	workflow_github_enabled: z.boolean(),
	workflow_github_owner: z.string().max(100).optional(),
	workflow_github_repo: z.string().max(100).optional(),
	workflow_github_workflow_id: z.string().max(200).optional(),
	workflow_github_ref: z.string().max(100),
	workflow_github_token: z.string().max(1024).optional(),
	clear_workflow_github_token: z.boolean().optional(),
	workflow_gitlab_enabled: z.boolean(),
	workflow_gitlab_base_url: z.string().max(255),
	workflow_gitlab_project_id: z.string().max(128).optional(),
	workflow_gitlab_ref: z.string().max(100),
	workflow_gitlab_trigger_token: z.string().max(1024).optional(),
	clear_workflow_gitlab_trigger_token: z.boolean().optional(),
	workflow_webhook_enabled: z.boolean(),
	workflow_webhook_url: z.string().max(500).optional(),
	workflow_webhook_bearer_token: z.string().max(1024).optional(),
	clear_workflow_webhook_bearer_token: z.boolean().optional(),
	digest_schedule: z.enum(['daily', 'weekly', 'disabled']),
	digest_hour: z.number().min(0).max(23),
	digest_minute: z.number().min(0).max(59),
	alert_on_budget_warning: z.boolean(),
	alert_on_budget_exceeded: z.boolean(),
	alert_on_zombie_detected: z.boolean()
});

export const CarbonSettingsSchema = z.object({
	carbon_budget_kg: z.number().min(1).max(100000),
	alert_threshold_percent: z.number().min(1).max(100),
	default_region: z.string().min(2),
	email_enabled: z.boolean(),
	email_recipients: z.string().optional()
});

export const LLMSettingsSchema = z.object({
	monthly_limit_usd: z.number().min(0).max(10000),
	alert_threshold_percent: z.number().min(0).max(100),
	hard_limit: z.boolean(),
	preferred_provider: z.string(),
	preferred_model: z.string(),
	openai_api_key: z.string().min(20).optional().or(z.literal('')),
	claude_api_key: z.string().min(20).optional().or(z.literal('')),
	google_api_key: z.string().min(20).optional().or(z.literal('')),
	groq_api_key: z.string().min(20).optional().or(z.literal(''))
});

export const ActiveOpsSettingsSchema = z.object({
	auto_pilot_enabled: z.boolean(),
	min_confidence_threshold: z.number().min(0.5).max(1.0),
	policy_enabled: z.boolean(),
	policy_block_production_destructive: z.boolean(),
	policy_require_gpu_override: z.boolean(),
	policy_low_confidence_warn_threshold: z.number().min(0.5).max(1.0),
	policy_violation_notify_slack: z.boolean(),
	policy_violation_notify_jira: z.boolean(),
	policy_escalation_required_role: z.enum(['owner', 'admin']),
	license_auto_reclaim_enabled: z.boolean(),
	license_inactive_threshold_days: z.number().min(7).max(365),
	license_reclaim_grace_period_days: z.number().min(1).max(30),
	license_downgrade_recommendations_enabled: z.boolean()
});
