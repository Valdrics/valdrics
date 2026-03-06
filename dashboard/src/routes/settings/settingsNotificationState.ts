import { INITIAL_NOTIFICATION_SETTINGS } from './settingsPageInitialState';

type NotificationSettingsState = typeof INITIAL_NOTIFICATION_SETTINGS;

type NotificationSavePayload = Record<string, unknown> & {
	jira_api_token?: string;
	clear_jira_api_token?: boolean;
	teams_webhook_url?: string;
	clear_teams_webhook_url?: boolean;
	workflow_github_token?: string;
	clear_workflow_github_token?: boolean;
	workflow_gitlab_trigger_token?: string;
	clear_workflow_gitlab_trigger_token?: boolean;
	workflow_webhook_bearer_token?: string;
	clear_workflow_webhook_bearer_token?: boolean;
};

export function mergeLoadedNotificationSettings(
	current: NotificationSettingsState,
	loaded: Record<string, unknown>
): NotificationSettingsState {
	return {
		...current,
		...loaded,
		slack_channel_override: (loaded.slack_channel_override as string | null) ?? '',
		jira_base_url: (loaded.jira_base_url as string | null) ?? '',
		jira_email: (loaded.jira_email as string | null) ?? '',
		jira_project_key: (loaded.jira_project_key as string | null) ?? '',
		jira_issue_type: (loaded.jira_issue_type as string | null) ?? 'Task',
		jira_api_token: '',
		clear_jira_api_token: false,
		teams_enabled: (loaded.teams_enabled as boolean | null) ?? false,
		teams_webhook_url: (loaded.teams_webhook_url as string | null) ?? '',
		clear_teams_webhook_url: false,
		has_teams_webhook_url: (loaded.has_teams_webhook_url as boolean | null) ?? false,
		workflow_github_enabled: (loaded.workflow_github_enabled as boolean | null) ?? false,
		workflow_github_owner: (loaded.workflow_github_owner as string | null) ?? '',
		workflow_github_repo: (loaded.workflow_github_repo as string | null) ?? '',
		workflow_github_workflow_id: (loaded.workflow_github_workflow_id as string | null) ?? '',
		workflow_github_ref: (loaded.workflow_github_ref as string | null) ?? 'main',
		workflow_github_token: '',
		clear_workflow_github_token: false,
		workflow_has_github_token: (loaded.workflow_has_github_token as boolean | null) ?? false,
		workflow_gitlab_enabled: (loaded.workflow_gitlab_enabled as boolean | null) ?? false,
		workflow_gitlab_base_url:
			(loaded.workflow_gitlab_base_url as string | null) ?? 'https://gitlab.com',
		workflow_gitlab_project_id: (loaded.workflow_gitlab_project_id as string | null) ?? '',
		workflow_gitlab_ref: (loaded.workflow_gitlab_ref as string | null) ?? 'main',
		workflow_gitlab_trigger_token: '',
		clear_workflow_gitlab_trigger_token: false,
		workflow_has_gitlab_trigger_token:
			(loaded.workflow_has_gitlab_trigger_token as boolean | null) ?? false,
		workflow_webhook_enabled: (loaded.workflow_webhook_enabled as boolean | null) ?? false,
		workflow_webhook_url: (loaded.workflow_webhook_url as string | null) ?? '',
		workflow_webhook_bearer_token: '',
		clear_workflow_webhook_bearer_token: false,
		workflow_has_webhook_bearer_token:
			(loaded.workflow_has_webhook_bearer_token as boolean | null) ?? false
	};
}

export function buildNotificationSavePayload(settings: NotificationSettingsState): NotificationSavePayload {
	return {
		...settings,
		slack_channel_override: settings.slack_channel_override || undefined,
		jira_base_url: settings.jira_base_url || undefined,
		jira_email: settings.jira_email || undefined,
		jira_project_key: settings.jira_project_key || undefined,
		jira_issue_type: settings.jira_issue_type || undefined,
		jira_api_token: settings.jira_api_token || undefined,
		teams_webhook_url: settings.teams_webhook_url || undefined,
		workflow_github_owner: settings.workflow_github_owner || undefined,
		workflow_github_repo: settings.workflow_github_repo || undefined,
		workflow_github_workflow_id: settings.workflow_github_workflow_id || undefined,
		workflow_github_ref: settings.workflow_github_ref || 'main',
		workflow_github_token: settings.workflow_github_token || undefined,
		workflow_gitlab_base_url: settings.workflow_gitlab_base_url || 'https://gitlab.com',
		workflow_gitlab_project_id: settings.workflow_gitlab_project_id || undefined,
		workflow_gitlab_ref: settings.workflow_gitlab_ref || 'main',
		workflow_gitlab_trigger_token: settings.workflow_gitlab_trigger_token || undefined,
		workflow_webhook_url: settings.workflow_webhook_url || undefined,
		workflow_webhook_bearer_token: settings.workflow_webhook_bearer_token || undefined
	};
}

export function applyPostSaveNotificationSettings(
	current: NotificationSettingsState,
	validated: NotificationSavePayload
): NotificationSettingsState {
	return {
		...current,
		has_jira_api_token: validated.jira_api_token
			? true
			: validated.clear_jira_api_token
				? false
				: current.has_jira_api_token,
		jira_api_token: '',
		clear_jira_api_token: false,
		has_teams_webhook_url: validated.teams_webhook_url
			? true
			: validated.clear_teams_webhook_url
				? false
				: current.has_teams_webhook_url,
		teams_webhook_url: '',
		clear_teams_webhook_url: false,
		workflow_has_github_token: validated.workflow_github_token
			? true
			: validated.clear_workflow_github_token
				? false
				: current.workflow_has_github_token,
		workflow_github_token: '',
		clear_workflow_github_token: false,
		workflow_has_gitlab_trigger_token: validated.workflow_gitlab_trigger_token
			? true
			: validated.clear_workflow_gitlab_trigger_token
				? false
				: current.workflow_has_gitlab_trigger_token,
		workflow_gitlab_trigger_token: '',
		clear_workflow_gitlab_trigger_token: false,
		workflow_has_webhook_bearer_token: validated.workflow_webhook_bearer_token
			? true
			: validated.clear_workflow_webhook_bearer_token
				? false
				: current.workflow_has_webhook_bearer_token,
		workflow_webhook_bearer_token: '',
		clear_workflow_webhook_bearer_token: false
	};
}
