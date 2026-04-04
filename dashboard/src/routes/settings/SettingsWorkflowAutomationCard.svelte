<script lang="ts">
	import { base } from '$app/paths';
	import { createLazyComponent } from '$lib/lazyComponent';
	import { getUpgradePrompt } from '$lib/pricing/upgradePrompt';
	import type { PolicyDiagnostics } from './settingsPageModels';
	import { INITIAL_NOTIFICATION_SETTINGS } from './settingsPageInitialState';

	type AsyncAction = () => void | Promise<void>;
	type NotificationSettingsState = typeof INITIAL_NOTIFICATION_SETTINGS;
	type SettingsWorkflowProviderFieldsProps = {
		settings: NotificationSettingsState;
		isProTier: boolean;
		testingWorkflow: boolean;
		testWorkflowDispatch: AsyncAction;
	};

	interface Props {
		settings: NotificationSettingsState;
		isProTier: boolean;
		testingWorkflow: boolean;
		diagnosticsLoading: boolean;
		policyDiagnostics: PolicyDiagnostics | null;
		testWorkflowDispatch: AsyncAction;
		runPolicyDiagnostics: AsyncAction;
	}

	let {
		settings = $bindable(),
		isProTier,
		testingWorkflow,
		diagnosticsLoading,
		policyDiagnostics,
		testWorkflowDispatch,
		runPolicyDiagnostics
	}: Props = $props();

	const upgradePrompt = getUpgradePrompt('pro', 'workflow automation');
	const loadSettingsWorkflowProviderFields =
		createLazyComponent<SettingsWorkflowProviderFieldsProps>(
			() => import('./SettingsWorkflowProviderFields.svelte')
		);
</script>

<div class="mt-4 rounded-xl border border-ink-700 p-4 bg-ink-900/30 space-y-4">
	<div class="flex items-center justify-between">
		<h4 class="text-sm font-semibold">Workflow Automation (GitHub/GitLab/Webhook)</h4>
		{#if !isProTier}
			<span class="badge badge-warning text-xs">Pro Plan Required</span>
		{/if}
	</div>
	<p class="text-xs text-ink-400">
		Route policy and remediation events into external CI runbooks using tenant-scoped credentials.
		This automation lane starts on Pro because it creates external tickets, dispatches, and approval
		activity.
	</p>

	{#if !isProTier}
		<div class="rounded-lg border border-ink-700/80 bg-ink-950/40 p-3 space-y-2">
			<p class="text-xs font-semibold text-white">{upgradePrompt.heading}</p>
			<p class="text-xs text-ink-400">{upgradePrompt.body}</p>
			<p class="text-[11px] text-ink-500">{upgradePrompt.footnote}</p>
			<a href={`${base}/billing`} class="btn btn-secondary text-xs w-full sm:!w-auto">
				{upgradePrompt.cta}
			</a>
		</div>
	{/if}

	{#await loadSettingsWorkflowProviderFields()}
		<div class="space-y-4" aria-hidden="true">
			<div class="rounded-xl border border-ink-700 bg-ink-900/20 p-4">
				<div class="skeleton mb-3 h-5 w-56"></div>
				<div class="skeleton mb-3 h-10 w-full"></div>
				<div class="skeleton h-24 w-full"></div>
			</div>
		</div>
	{:then module}
		{@const SettingsWorkflowProviderFields = module.default}
		<SettingsWorkflowProviderFields
			bind:settings
			{isProTier}
			{testingWorkflow}
			{testWorkflowDispatch}
		/>
	{/await}
</div>

<div class="mt-4 rounded-xl border border-ink-700 p-4 bg-ink-900/30">
	<div class="flex flex-wrap items-center justify-between gap-3 mb-3">
		<h4 class="text-sm font-semibold">Policy Notification Diagnostics</h4>
		<button
			type="button"
			class="btn btn-ghost"
			onclick={runPolicyDiagnostics}
			disabled={diagnosticsLoading}
			aria-label="Run policy notification diagnostics"
		>
			{diagnosticsLoading ? '⏳ Checking...' : '🔍 Run Diagnostics'}
		</button>
	</div>

	{#if policyDiagnostics}
		<p class="text-xs text-ink-400 mb-3">
			Tier: <span class="font-semibold uppercase">{policyDiagnostics.tier}</span>
			• Policy enabled: {policyDiagnostics.policy_enabled ? 'yes' : 'no'}
		</p>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
			<div class="rounded-lg border border-ink-700 p-3">
				<div class="flex items-center justify-between">
					<span class="font-medium">Slack</span>
					<span class={policyDiagnostics.slack.ready ? 'text-success-400' : 'text-warning-400'}>
						{policyDiagnostics.slack.ready ? 'Ready' : 'Blocked'}
					</span>
				</div>
				{#if policyDiagnostics.slack.reasons.length > 0}
					<p class="text-xs text-ink-400 mt-2 break-words">
						{policyDiagnostics.slack.reasons.join(', ')}
					</p>
				{/if}
			</div>

			<div class="rounded-lg border border-ink-700 p-3">
				<div class="flex items-center justify-between">
					<span class="font-medium">Jira</span>
					<span class={policyDiagnostics.jira.ready ? 'text-success-400' : 'text-warning-400'}>
						{policyDiagnostics.jira.ready ? 'Ready' : 'Blocked'}
					</span>
				</div>
				{#if policyDiagnostics.jira.reasons.length > 0}
					<p class="text-xs text-ink-400 mt-2 break-words">
						{policyDiagnostics.jira.reasons.join(', ')}
					</p>
				{/if}
			</div>
		</div>
	{/if}
</div>
