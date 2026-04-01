<script lang="ts">
	import { onMount } from 'svelte';
	import { createLazyComponent } from '$lib/lazyComponent';
	import {
		INITIAL_ACTIVEOPS_SETTINGS,
		INITIAL_LLM_SETTINGS,
		INITIAL_NOTIFICATION_SETTINGS,
		INITIAL_PROVIDER_MODELS
	} from './settingsPageInitialState';
	import type { PolicyDiagnostics, SafetyStatus } from './settingsPageModels';

	type AsyncAction = () => void | Promise<void>;
	type NotificationSettingsState = typeof INITIAL_NOTIFICATION_SETTINGS;
	type LlmSettingsState = typeof INITIAL_LLM_SETTINGS;
	type ActiveOpsSettingsState = typeof INITIAL_ACTIVEOPS_SETTINGS;
	type ProviderModelsState = typeof INITIAL_PROVIDER_MODELS;
	type TieredSettingsCardProps = {
		accessToken?: string;
		tier?: string;
	};
	type SettingsNotificationControlsProps = {
		data: {
			user?: unknown;
			session?: { access_token?: string };
			subscription?: { tier?: string };
			profile?: { persona?: string };
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
	};

	let {
		data,
		llmSettings = $bindable(),
		loadingLLM,
		savingLLM,
		providerModels,
		saveLLMSettings,
		activeOpsSettings = $bindable(),
		loadingActiveOps,
		savingActiveOps,
		saveActiveOpsSettings,
		loadingSafety,
		resettingSafety,
		loadSafetyStatus,
		resetSafetyCircuitBreaker,
		safetyError,
		safetySuccess,
		safetyStatus,
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
	}: {
		data: {
			user?: unknown;
			session?: { access_token?: string };
			subscription?: { tier?: string };
			profile?: { persona?: string };
		};
		llmSettings: LlmSettingsState;
		loadingLLM: boolean;
		savingLLM: boolean;
		providerModels: ProviderModelsState;
		saveLLMSettings: AsyncAction;
		activeOpsSettings: ActiveOpsSettingsState;
		loadingActiveOps: boolean;
		savingActiveOps: boolean;
		saveActiveOpsSettings: AsyncAction;
		loadingSafety: boolean;
		resettingSafety: boolean;
		loadSafetyStatus: AsyncAction;
		resetSafetyCircuitBreaker: AsyncAction;
		safetyError: string;
		safetySuccess: string;
		safetyStatus: SafetyStatus | null;
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
	} = $props();

	const loadIdentitySettingsCard = createLazyComponent<TieredSettingsCardProps>(
		() => import('$lib/components/IdentitySettingsCard.svelte')
	);
	const loadEnforcementSettingsCard = createLazyComponent<TieredSettingsCardProps>(
		() => import('$lib/components/EnforcementSettingsCard.svelte')
	);
	const loadEnforcementOpsCard = createLazyComponent<TieredSettingsCardProps>(
		() => import('$lib/components/EnforcementOpsCard.svelte')
	);
	const loadSettingsAiStrategyCard = createLazyComponent<{
		loadingLLM: boolean;
		llmSettings: LlmSettingsState;
		providerModels: ProviderModelsState;
		saveLLMSettings: AsyncAction;
		savingLLM: boolean;
	}>(() => import('./SettingsAiStrategyCard.svelte'));
	const loadSettingsActiveOpsCard = createLazyComponent<{
		data: {
			user?: unknown;
			session?: { access_token?: string };
			subscription?: { tier?: string };
			profile?: { persona?: string };
		};
		loadingActiveOps: boolean;
		activeOpsSettings: ActiveOpsSettingsState;
		saveActiveOpsSettings: AsyncAction;
		savingActiveOps: boolean;
	}>(() => import('./SettingsActiveOpsCard.svelte'));
	const loadSettingsSafetyControlsCard = createLazyComponent<{
		loadingSafety: boolean;
		resettingSafety: boolean;
		loadSafetyStatus: AsyncAction;
		resetSafetyCircuitBreaker: AsyncAction;
		safetyError: string;
		safetySuccess: string;
		safetyStatus: SafetyStatus | null;
	}>(() => import('./SettingsSafetyControlsCard.svelte'));
	const loadSettingsNotificationControls = createLazyComponent<SettingsNotificationControlsProps>(
		() => import('./SettingsNotificationControls.svelte')
	);

	let advancedSettingsAnchor: HTMLDivElement | null = $state(null);
	let advancedSettingsVisible = $state(false);

	onMount(() => {
		if (import.meta.env.MODE === 'test' || typeof IntersectionObserver === 'undefined') {
			advancedSettingsVisible = true;
			return;
		}

		const observer = new IntersectionObserver(
			(entries) => {
				if (entries.some((entry) => entry.isIntersecting)) {
					advancedSettingsVisible = true;
					observer.disconnect();
				}
			},
			{ rootMargin: '320px 0px' }
		);

		if (advancedSettingsAnchor) {
			observer.observe(advancedSettingsAnchor);
		}

		return () => observer.disconnect();
	});
</script>

{#await loadIdentitySettingsCard()}
	<div class="card">
		<div class="skeleton h-6 w-40 mb-4"></div>
		<div class="skeleton h-4 w-full mb-2"></div>
		<div class="skeleton h-4 w-3/4"></div>
	</div>
{:then module}
	{@const IdentitySettingsCard = module.default}
	<IdentitySettingsCard accessToken={data.session?.access_token} tier={data.subscription?.tier} />
{:catch}
	<div class="card">
		<div class="skeleton h-6 w-40 mb-4"></div>
		<div class="skeleton h-4 w-full mb-2"></div>
		<div class="skeleton h-4 w-3/4"></div>
	</div>
{/await}

{#await loadEnforcementSettingsCard()}
	<div class="card">
		<div class="skeleton h-6 w-48 mb-4"></div>
		<div class="skeleton h-4 w-full mb-2"></div>
		<div class="skeleton h-4 w-2/3"></div>
	</div>
{:then module}
	{@const EnforcementSettingsCard = module.default}
	<EnforcementSettingsCard
		accessToken={data.session?.access_token}
		tier={data.subscription?.tier}
	/>
{:catch}
	<div class="card">
		<div class="skeleton h-6 w-48 mb-4"></div>
		<div class="skeleton h-4 w-full mb-2"></div>
		<div class="skeleton h-4 w-2/3"></div>
	</div>
{/await}

{#await loadEnforcementOpsCard()}
	<div class="card">
		<div class="skeleton h-6 w-48 mb-4"></div>
		<div class="skeleton h-4 w-full mb-2"></div>
		<div class="skeleton h-4 w-2/3"></div>
	</div>
{:then module}
	{@const EnforcementOpsCard = module.default}
	<EnforcementOpsCard accessToken={data.session?.access_token} tier={data.subscription?.tier} />
{:catch}
	<div class="card">
		<div class="skeleton h-6 w-48 mb-4"></div>
		<div class="skeleton h-4 w-full mb-2"></div>
		<div class="skeleton h-4 w-2/3"></div>
	</div>
{/await}

<div bind:this={advancedSettingsAnchor}>
	{#if advancedSettingsVisible}
		{#await loadSettingsAiStrategyCard()}
			<div class="card">
				<div class="skeleton h-6 w-48 mb-4"></div>
				<div class="skeleton h-24 rounded-2xl"></div>
			</div>
		{:then module}
			{@const SettingsAiStrategyCard = module.default}
			<SettingsAiStrategyCard
				{loadingLLM}
				bind:llmSettings
				{providerModels}
				{saveLLMSettings}
				{savingLLM}
			/>
		{:catch}
			<div class="card">
				<div class="skeleton h-6 w-48 mb-4"></div>
				<div class="skeleton h-24 rounded-2xl"></div>
			</div>
		{/await}

		{#await loadSettingsActiveOpsCard()}
			<div class="card">
				<div class="skeleton h-6 w-48 mb-4"></div>
				<div class="skeleton h-24 rounded-2xl"></div>
			</div>
		{:then module}
			{@const SettingsActiveOpsCard = module.default}
			<SettingsActiveOpsCard
				{data}
				{loadingActiveOps}
				bind:activeOpsSettings
				{saveActiveOpsSettings}
				{savingActiveOps}
			/>
		{:catch}
			<div class="card">
				<div class="skeleton h-6 w-48 mb-4"></div>
				<div class="skeleton h-24 rounded-2xl"></div>
			</div>
		{/await}

		{#await loadSettingsSafetyControlsCard()}
			<div class="card">
				<div class="skeleton h-6 w-56 mb-4"></div>
				<div class="skeleton h-20 rounded-2xl"></div>
			</div>
		{:then module}
			{@const SettingsSafetyControlsCard = module.default}
			<SettingsSafetyControlsCard
				{loadingSafety}
				{resettingSafety}
				{loadSafetyStatus}
				{resetSafetyCircuitBreaker}
				{safetyError}
				{safetySuccess}
				{safetyStatus}
			/>
		{:catch}
			<div class="card">
				<div class="skeleton h-6 w-56 mb-4"></div>
				<div class="skeleton h-20 rounded-2xl"></div>
			</div>
		{/await}

		{#await loadSettingsNotificationControls()}
			<div class="card">
				<div class="skeleton h-6 w-52 mb-4"></div>
				<div class="skeleton h-4 w-full mb-2"></div>
				<div class="skeleton h-4 w-3/4"></div>
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
		{:catch}
			<div class="card">
				<div class="skeleton h-6 w-52 mb-4"></div>
				<div class="skeleton h-4 w-full mb-2"></div>
				<div class="skeleton h-4 w-3/4"></div>
			</div>
		{/await}
	{:else}
		<div class="card">
			<div class="skeleton h-6 w-48 mb-4"></div>
			<div class="skeleton h-24 rounded-2xl"></div>
		</div>
	{/if}
</div>
