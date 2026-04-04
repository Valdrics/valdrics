<script lang="ts">
	import { onMount } from 'svelte';
	import { createLazyComponent } from '$lib/lazyComponent';
	import { INITIAL_NOTIFICATION_SETTINGS } from './settingsPageInitialState';

	type NotificationSettingsState = typeof INITIAL_NOTIFICATION_SETTINGS;
	type PolicyDiagnostics = import('./settingsPageModels').PolicyDiagnostics;
	type NotificationRuntimeModule = typeof import('./settingsNotificationRuntime');
	type SettingsNotificationControlsProps = {
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
		testSlack: () => void | Promise<void>;
		testJira: () => void | Promise<void>;
		testTeams: () => void | Promise<void>;
		testWorkflowDispatch: () => void | Promise<void>;
		runPolicyDiagnostics: () => void | Promise<void>;
		saveSettings: () => void | Promise<void>;
		saving: boolean;
		onSaveSettings?: () => void | Promise<void>;
	};
	const loadSettingsNotificationControls = createLazyComponent<SettingsNotificationControlsProps>(
		() => import('./SettingsNotificationControls.svelte')
	);

	let {
		data
	}: {
		data: {
			user?: unknown;
			session?: { access_token?: string };
			subscription?: { tier?: string };
			profile?: { persona?: string };
		};
	} = $props();

	let settings = $state<NotificationSettingsState>({ ...INITIAL_NOTIFICATION_SETTINGS });
	let testing = $state(false);
	let testingJira = $state(false);
	let testingTeams = $state(false);
	let testingWorkflow = $state(false);
	let diagnosticsLoading = $state(false);
	let policyDiagnostics = $state<PolicyDiagnostics | null>(null);
	let saving = $state(false);
	let error = $state('');
	let success = $state('');
	let notificationRuntimePromise: Promise<NotificationRuntimeModule> | null = null;

	function loadNotificationRuntime() {
		if (!notificationRuntimePromise) {
			notificationRuntimePromise = import('./settingsNotificationRuntime');
		}
		return notificationRuntimePromise;
	}

	async function loadSettings() {
		const runtime = await loadNotificationRuntime();
		const result = await runtime.loadNotificationSettings(data.session?.access_token, settings);
		settings = result.settings;
		error = result.error;
	}

	async function saveSettings() {
		saving = true;
		error = '';
		success = '';
		try {
			const runtime = await loadNotificationRuntime();
			settings = await runtime.saveNotificationSettings(data.session?.access_token, settings);
			success = 'General settings saved!';
			setTimeout(() => (success = ''), 3000);
		} catch (nextError) {
			error = (nextError as Error).message;
		} finally {
			saving = false;
		}
	}

	async function runNotificationTest(
		path: string,
		successMessage: string,
		setLoadingState: (value: boolean) => void,
		fallbackMessage: string
	) {
		setLoadingState(true);
		error = '';
		try {
			const runtime = await loadNotificationRuntime();
			await runtime.runNotificationTest(data.session?.access_token, path, fallbackMessage);
			success = successMessage;
			setTimeout(() => (success = ''), 3000);
		} catch (nextError) {
			const err = nextError as Error;
			error = err.message;
		} finally {
			setLoadingState(false);
		}
	}

	const testSlack = () =>
		runNotificationTest(
			'/settings/notifications/test-slack',
			'Test notification sent to Slack!',
			(value) => (testing = value),
			'Failed to send test notification'
		);
	const testJira = () =>
		runNotificationTest(
			'/settings/notifications/test-jira',
			'Test issue created in Jira!',
			(value) => (testingJira = value),
			'Failed to send Jira test issue'
		);
	const testTeams = () =>
		runNotificationTest(
			'/settings/notifications/test-teams',
			'Test notification sent to Teams!',
			(value) => (testingTeams = value),
			'Failed to send Teams test notification'
		);
	const testWorkflowDispatch = () =>
		runNotificationTest(
			'/settings/notifications/test-workflow',
			'Workflow test event dispatched!',
			(value) => (testingWorkflow = value),
			'Failed to dispatch workflow test event'
		);

	async function runPolicyDiagnostics() {
		diagnosticsLoading = true;
		error = '';
		try {
			const runtime = await loadNotificationRuntime();
			policyDiagnostics = await runtime.runNotificationPolicyDiagnostics(
				data.session?.access_token
			);
			success = 'Policy diagnostics refreshed.';
			setTimeout(() => (success = ''), 2000);
		} catch (nextError) {
			const err = nextError as Error;
			error = err.message;
		} finally {
			diagnosticsLoading = false;
		}
	}

	onMount(() => {
		if (!data.user) {
			return;
		}
		void loadSettings();
	});
</script>

<div class="space-y-4">
	{#if error}
		<div role="alert" class="card border-danger-500/50 bg-danger-500/10">
			<p class="text-danger-400">{error}</p>
		</div>
	{/if}

	{#if success}
		<div role="status" class="card border-success-500/50 bg-success-500/10">
			<p class="text-success-400">{success}</p>
		</div>
	{/if}

	{#await loadSettingsNotificationControls()}
		<div class="space-y-4" aria-hidden="true">
			<div class="card">
				<div class="skeleton mb-3 h-6 w-48"></div>
				<div class="skeleton mb-3 h-4 w-full"></div>
				<div class="skeleton h-10 w-full"></div>
			</div>
			<div class="card">
				<div class="skeleton mb-3 h-6 w-40"></div>
				<div class="skeleton h-32 w-full"></div>
			</div>
		</div>
	{:then module}
		{@const SettingsNotificationControls = module.default}
		<SettingsNotificationControls
			{data}
			bind:settings
			{testing}
			{testingJira}
			{testingTeams}
			{testingWorkflow}
			{diagnosticsLoading}
			{policyDiagnostics}
			{testSlack}
			{testJira}
			{testTeams}
			{testWorkflowDispatch}
			{runPolicyDiagnostics}
			{saveSettings}
			{saving}
		/>
	{/await}
</div>
