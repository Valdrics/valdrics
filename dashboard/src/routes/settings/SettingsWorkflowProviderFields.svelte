<script lang="ts">
	import { INITIAL_NOTIFICATION_SETTINGS } from './settingsPageInitialState';

	type AsyncAction = () => void | Promise<void>;
	type NotificationSettingsState = typeof INITIAL_NOTIFICATION_SETTINGS;

	interface Props {
		settings: NotificationSettingsState;
		isProTier: boolean;
		testingWorkflow: boolean;
		testWorkflowDispatch: AsyncAction;
	}

	let {
		settings = $bindable(),
		isProTier,
		testingWorkflow,
		testWorkflowDispatch
	}: Props = $props();
</script>

<label class="flex items-center gap-3 cursor-pointer">
	<input
		type="checkbox"
		bind:checked={settings.workflow_github_enabled}
		class="toggle"
		disabled={!isProTier}
		aria-label="Enable GitHub workflow dispatch"
	/>
	<span>Enable GitHub Actions workflow dispatch</span>
</label>
<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
	<div class="form-group">
		<label for="workflow_github_owner">GitHub Owner</label>
		<input
			type="text"
			id="workflow_github_owner"
			bind:value={settings.workflow_github_owner}
			placeholder="Valdrics"
			disabled={!settings.workflow_github_enabled || !isProTier}
		/>
	</div>
	<div class="form-group">
		<label for="workflow_github_repo">GitHub Repo</label>
		<input
			type="text"
			id="workflow_github_repo"
			bind:value={settings.workflow_github_repo}
			placeholder="valdrics"
			disabled={!settings.workflow_github_enabled || !isProTier}
		/>
	</div>
	<div class="form-group">
		<label for="workflow_github_workflow_id">Workflow ID/File</label>
		<input
			type="text"
			id="workflow_github_workflow_id"
			bind:value={settings.workflow_github_workflow_id}
			placeholder="remediation.yml"
			disabled={!settings.workflow_github_enabled || !isProTier}
		/>
	</div>
	<div class="form-group">
		<label for="workflow_github_ref">Ref</label>
		<input
			type="text"
			id="workflow_github_ref"
			bind:value={settings.workflow_github_ref}
			placeholder="main"
			disabled={!settings.workflow_github_enabled || !isProTier}
		/>
	</div>
</div>
<div class="form-group">
	<label for="workflow_github_token">GitHub Token</label>
	<input
		type="password"
		id="workflow_github_token"
		bind:value={settings.workflow_github_token}
		placeholder={settings.workflow_has_github_token
			? 'Stored token exists. Enter new token to rotate.'
			: 'Enter GitHub token'}
		disabled={!settings.workflow_github_enabled || !isProTier}
	/>
</div>
<label class="flex items-center gap-3 cursor-pointer">
	<input
		type="checkbox"
		bind:checked={settings.clear_workflow_github_token}
		class="toggle"
		disabled={!settings.workflow_github_enabled ||
			!settings.workflow_has_github_token ||
			!isProTier}
	/>
	<span>Clear stored GitHub token</span>
</label>

<div class="h-px bg-ink-700"></div>

<label class="flex items-center gap-3 cursor-pointer">
	<input
		type="checkbox"
		bind:checked={settings.workflow_gitlab_enabled}
		class="toggle"
		disabled={!isProTier}
		aria-label="Enable GitLab workflow dispatch"
	/>
	<span>Enable GitLab CI trigger dispatch</span>
</label>
<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
	<div class="form-group">
		<label for="workflow_gitlab_base_url">GitLab Base URL</label>
		<input
			type="url"
			id="workflow_gitlab_base_url"
			bind:value={settings.workflow_gitlab_base_url}
			placeholder="https://gitlab.com"
			disabled={!settings.workflow_gitlab_enabled || !isProTier}
		/>
	</div>
	<div class="form-group">
		<label for="workflow_gitlab_project_id">Project ID/Path</label>
		<input
			type="text"
			id="workflow_gitlab_project_id"
			bind:value={settings.workflow_gitlab_project_id}
			placeholder="12345"
			disabled={!settings.workflow_gitlab_enabled || !isProTier}
		/>
	</div>
	<div class="form-group">
		<label for="workflow_gitlab_ref">Ref</label>
		<input
			type="text"
			id="workflow_gitlab_ref"
			bind:value={settings.workflow_gitlab_ref}
			placeholder="main"
			disabled={!settings.workflow_gitlab_enabled || !isProTier}
		/>
	</div>
	<div class="form-group">
		<label for="workflow_gitlab_trigger_token">Trigger Token</label>
		<input
			type="password"
			id="workflow_gitlab_trigger_token"
			bind:value={settings.workflow_gitlab_trigger_token}
			placeholder={settings.workflow_has_gitlab_trigger_token
				? 'Stored token exists. Enter new token to rotate.'
				: 'Enter GitLab trigger token'}
			disabled={!settings.workflow_gitlab_enabled || !isProTier}
		/>
	</div>
</div>
<label class="flex items-center gap-3 cursor-pointer">
	<input
		type="checkbox"
		bind:checked={settings.clear_workflow_gitlab_trigger_token}
		class="toggle"
		disabled={!settings.workflow_gitlab_enabled ||
			!settings.workflow_has_gitlab_trigger_token ||
			!isProTier}
	/>
	<span>Clear stored GitLab trigger token</span>
</label>

<div class="h-px bg-ink-700"></div>

<label class="flex items-center gap-3 cursor-pointer">
	<input
		type="checkbox"
		bind:checked={settings.workflow_webhook_enabled}
		class="toggle"
		disabled={!isProTier}
		aria-label="Enable webhook workflow dispatch"
	/>
	<span>Enable Generic CI Webhook dispatch</span>
</label>
<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
	<div class="form-group">
		<label for="workflow_webhook_url">Webhook URL</label>
		<input
			type="url"
			id="workflow_webhook_url"
			bind:value={settings.workflow_webhook_url}
			placeholder="https://ci.example.com/hooks/valdrics"
			disabled={!settings.workflow_webhook_enabled || !isProTier}
		/>
	</div>
	<div class="form-group">
		<label for="workflow_webhook_bearer_token">Bearer Token (optional)</label>
		<input
			type="password"
			id="workflow_webhook_bearer_token"
			bind:value={settings.workflow_webhook_bearer_token}
			placeholder={settings.workflow_has_webhook_bearer_token
				? 'Stored token exists. Enter new token to rotate.'
				: 'Enter bearer token (optional)'}
			disabled={!settings.workflow_webhook_enabled || !isProTier}
		/>
	</div>
</div>
<label class="flex items-center gap-3 cursor-pointer">
	<input
		type="checkbox"
		bind:checked={settings.clear_workflow_webhook_bearer_token}
		class="toggle"
		disabled={!settings.workflow_webhook_enabled ||
			!settings.workflow_has_webhook_bearer_token ||
			!isProTier}
	/>
	<span>Clear stored webhook bearer token</span>
</label>

<button
	type="button"
	class="btn btn-secondary"
	onclick={testWorkflowDispatch}
	disabled={testingWorkflow || !isProTier}
	aria-label="Send test workflow event"
>
	{testingWorkflow ? '⏳ Sending...' : '🧪 Send Test Workflow Event'}
</button>
