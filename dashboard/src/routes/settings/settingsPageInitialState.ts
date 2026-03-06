export const INITIAL_NOTIFICATION_SETTINGS = {
	slack_enabled: true,
	slack_channel_override: '',
	jira_enabled: false,
	jira_base_url: '',
	jira_email: '',
	jira_project_key: '',
	jira_issue_type: 'Task',
	jira_api_token: '',
	clear_jira_api_token: false,
	has_jira_api_token: false,
	teams_enabled: false,
	teams_webhook_url: '',
	clear_teams_webhook_url: false,
	has_teams_webhook_url: false,
	workflow_github_enabled: false,
	workflow_github_owner: '',
	workflow_github_repo: '',
	workflow_github_workflow_id: '',
	workflow_github_ref: 'main',
	workflow_github_token: '',
	clear_workflow_github_token: false,
	workflow_has_github_token: false,
	workflow_gitlab_enabled: false,
	workflow_gitlab_base_url: 'https://gitlab.com',
	workflow_gitlab_project_id: '',
	workflow_gitlab_ref: 'main',
	workflow_gitlab_trigger_token: '',
	clear_workflow_gitlab_trigger_token: false,
	workflow_has_gitlab_trigger_token: false,
	workflow_webhook_enabled: false,
	workflow_webhook_url: '',
	workflow_webhook_bearer_token: '',
	clear_workflow_webhook_bearer_token: false,
	workflow_has_webhook_bearer_token: false,
	digest_schedule: 'daily' as 'daily' | 'weekly' | 'disabled',
	digest_hour: 9,
	digest_minute: 0,
	alert_on_budget_warning: true,
	alert_on_budget_exceeded: true,
	alert_on_zombie_detected: true
};

export const INITIAL_LLM_SETTINGS = {
	monthly_limit_usd: 10.0,
	alert_threshold_percent: 80,
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
};

export const INITIAL_ACTIVEOPS_SETTINGS = {
	auto_pilot_enabled: false,
	min_confidence_threshold: 0.95,
	policy_enabled: true,
	policy_block_production_destructive: true,
	policy_require_gpu_override: true,
	policy_low_confidence_warn_threshold: 0.9,
	policy_violation_notify_slack: true,
	policy_violation_notify_jira: false,
	policy_escalation_required_role: 'owner' as const,
	license_auto_reclaim_enabled: false,
	license_inactive_threshold_days: 30,
	license_reclaim_grace_period_days: 3,
	license_downgrade_recommendations_enabled: true
};

export const INITIAL_PROVIDER_MODELS = {
	groq: [],
	openai: [],
	anthropic: [],
	google: []
};

export const INITIAL_CARBON_SETTINGS = {
	carbon_budget_kg: 100,
	alert_threshold_percent: 80,
	default_region: 'us-east-1',
	email_enabled: false,
	email_recipients: ''
};
