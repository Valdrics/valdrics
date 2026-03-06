<script lang="ts">
	import { type PolicyDiagnostics } from './settingsPageSchemas';
	import SettingsDigestAlertCard from './SettingsDigestAlertCard.svelte';
	import { INITIAL_NOTIFICATION_SETTINGS } from './settingsPageInitialState';
	import SettingsWorkflowAutomationCard from './SettingsWorkflowAutomationCard.svelte';

	type AsyncAction = () => void | Promise<void>;
	type NotificationSettingsState = typeof INITIAL_NOTIFICATION_SETTINGS;

	interface Props {
		data: {
			subscription?: {
				tier?: string;
			};
		};
		settings: NotificationSettingsState;
		testing: boolean;
		testingJira: boolean;
		testingTeams: boolean;
		testingWorkflow: boolean;
		diagnosticsLoading: boolean;
		policyDiagnostics: PolicyDiagnostics | null;
		testSlack: AsyncAction;
		testJira: AsyncAction;
		testTeams: AsyncAction;
		testWorkflowDispatch: AsyncAction;
		runPolicyDiagnostics: AsyncAction;
		saveSettings: AsyncAction;
		saving: boolean;
	}

	let {
		data,
		settings = $bindable(),
		testing,
		testingJira,
		testingTeams,
		testingWorkflow,
		diagnosticsLoading,
		policyDiagnostics,
		testSlack,
		testJira,
		testTeams,
		testWorkflowDispatch,
		runPolicyDiagnostics,
		saveSettings,
		saving
	}: Props = $props();

	const isProTier = $derived(['pro', 'enterprise'].includes(data.subscription?.tier ?? ''));
</script>

			<!-- Slack Settings -->
			<div class="card stagger-enter">
				<h2 class="text-lg font-semibold mb-5 flex items-center gap-2">
					<span>💬</span> Slack Notifications
				</h2>

				<div class="space-y-4">
					<label class="flex items-center gap-3 cursor-pointer">
						<input
							type="checkbox"
							bind:checked={settings.slack_enabled}
							class="toggle"
							aria-label="Enable Slack notifications"
						/>
						<span>Enable Slack notifications</span>
					</label>

					<div class="form-group">
						<label for="channel">Channel Override (optional)</label>
						<input
							type="text"
							id="channel"
							bind:value={settings.slack_channel_override}
							placeholder="C01234ABCDE"
							disabled={!settings.slack_enabled}
							aria-label="Slack channel ID override"
						/>
						<p class="text-xs text-ink-500 mt-1">Leave empty to use the default channel</p>
					</div>

					<button
						type="button"
						class="btn btn-secondary"
						onclick={testSlack}
						disabled={!settings.slack_enabled || testing}
						aria-label="Send test Slack notification"
					>
						{testing ? '⏳ Sending...' : '🧪 Send Test Notification'}
					</button>

					<div class="pt-4 border-t border-ink-200">
						<h3 class="text-sm font-semibold mb-3">Jira Incident Routing (Pro+)</h3>
						<label class="flex items-center gap-3 cursor-pointer mb-3">
							<input
								type="checkbox"
								bind:checked={settings.jira_enabled}
								class="toggle"
								disabled={!isProTier}
								aria-label="Enable Jira policy notifications"
							/>
							<span>Enable Jira policy notifications</span>
						</label>

						<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
							<div class="form-group">
								<label for="jira_base_url">Jira Base URL</label>
								<input
									type="url"
									id="jira_base_url"
									bind:value={settings.jira_base_url}
									placeholder="https://your-org.atlassian.net"
									disabled={!settings.jira_enabled ||
										!isProTier}
									aria-label="Jira base URL"
								/>
							</div>
							<div class="form-group">
								<label for="jira_email">Jira Account Email</label>
								<input
									type="email"
									id="jira_email"
									bind:value={settings.jira_email}
									placeholder="jira@company.com"
									disabled={!settings.jira_enabled ||
										!isProTier}
									aria-label="Jira account email"
								/>
							</div>
							<div class="form-group">
								<label for="jira_project_key">Jira Project Key</label>
								<input
									type="text"
									id="jira_project_key"
									bind:value={settings.jira_project_key}
									placeholder="FINOPS"
									disabled={!settings.jira_enabled ||
										!isProTier}
									aria-label="Jira project key"
								/>
							</div>
							<div class="form-group">
								<label for="jira_issue_type">Issue Type</label>
								<input
									type="text"
									id="jira_issue_type"
									bind:value={settings.jira_issue_type}
									placeholder="Task"
									disabled={!settings.jira_enabled ||
										!isProTier}
									aria-label="Jira issue type"
								/>
							</div>
						</div>

						<div class="form-group">
							<label for="jira_api_token">Jira API Token</label>
							<input
								type="password"
								id="jira_api_token"
								bind:value={settings.jira_api_token}
								placeholder={settings.has_jira_api_token
									? 'Stored token exists. Enter new token to rotate.'
									: 'Enter Jira API token'}
								disabled={!settings.jira_enabled ||
									!isProTier}
								aria-label="Jira API token"
							/>
						</div>
						<label class="flex items-center gap-3 cursor-pointer mb-3">
							<input
								type="checkbox"
								bind:checked={settings.clear_jira_api_token}
								class="toggle"
								disabled={!settings.jira_enabled ||
									!settings.has_jira_api_token ||
									!isProTier}
								aria-label="Clear stored Jira API token"
							/>
							<span>Clear stored Jira token</span>
						</label>
						<button
							type="button"
							class="btn btn-secondary"
							onclick={testJira}
							disabled={!settings.jira_enabled ||
								testingJira ||
								!isProTier}
							aria-label="Send test Jira issue"
						>
							{testingJira ? '⏳ Sending...' : '🧪 Send Test Jira Issue'}
						</button>

						<div class="pt-4 border-t border-ink-200 mt-4">
							<h3 class="text-sm font-semibold mb-3">Microsoft Teams Incident Routing (Pro+)</h3>
							<label class="flex items-center gap-3 cursor-pointer mb-3">
								<input
									type="checkbox"
									bind:checked={settings.teams_enabled}
									class="toggle"
									disabled={!isProTier}
									aria-label="Enable Teams policy notifications"
								/>
								<span>Enable Teams policy notifications</span>
							</label>
							<div class="form-group">
								<label for="teams_webhook_url">Teams Webhook URL</label>
								<input
									type="password"
									id="teams_webhook_url"
									bind:value={settings.teams_webhook_url}
									placeholder={settings.has_teams_webhook_url
										? 'Stored webhook exists. Enter new URL to rotate.'
										: 'https://<tenant>.webhook.office.com/...'}
									disabled={!settings.teams_enabled ||
										!isProTier}
									aria-label="Teams webhook URL"
								/>
								<p class="text-xs text-ink-500 mt-1">
									Webhook URL is encrypted at rest and used for policy/remediation alerts.
								</p>
							</div>
							<label class="flex items-center gap-3 cursor-pointer mb-3">
								<input
									type="checkbox"
									bind:checked={settings.clear_teams_webhook_url}
									class="toggle"
									disabled={!settings.teams_enabled ||
										!settings.has_teams_webhook_url ||
										!isProTier}
									aria-label="Clear stored Teams webhook URL"
								/>
								<span>Clear stored Teams webhook URL</span>
							</label>
							<button
								type="button"
								class="btn btn-secondary"
								onclick={testTeams}
								disabled={!settings.teams_enabled ||
									testingTeams ||
									!isProTier}
								aria-label="Send test Teams notification"
							>
								{testingTeams ? '⏳ Sending...' : '🧪 Send Test Teams Notification'}
							</button>
						</div>

						<SettingsWorkflowAutomationCard
							bind:settings={settings}
							{isProTier}
							{testingWorkflow}
							{diagnosticsLoading}
							{policyDiagnostics}
							{testWorkflowDispatch}
							{runPolicyDiagnostics}
						/>
					</div>
				</div>
			</div>

			<SettingsDigestAlertCard bind:settings={settings} {saveSettings} {saving} />
