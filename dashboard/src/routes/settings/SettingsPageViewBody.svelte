<script lang="ts">
	import { base } from '$app/paths';
	import AuthGate from '$lib/components/AuthGate.svelte';
	import EnforcementOpsCard from '$lib/components/EnforcementOpsCard.svelte';
	import EnforcementSettingsCard from '$lib/components/EnforcementSettingsCard.svelte';
	import IdentitySettingsCard from '$lib/components/IdentitySettingsCard.svelte';
	import { getUpgradePrompt } from '$lib/pricing/upgradePrompt';
	import SettingsActiveOpsCard from './SettingsActiveOpsCard.svelte';
	import SettingsAiStrategyCard from './SettingsAiStrategyCard.svelte';
	import { INITIAL_ACTIVEOPS_SETTINGS, INITIAL_CARBON_SETTINGS, INITIAL_LLM_SETTINGS, INITIAL_NOTIFICATION_SETTINGS, INITIAL_PROVIDER_MODELS } from './settingsPageInitialState';
	import SettingsNotificationControls from './SettingsNotificationControls.svelte';
	import type { PolicyDiagnostics, SafetyStatus } from './settingsPageSchemas';
	import SettingsSafetyControlsCard from './SettingsSafetyControlsCard.svelte';

	type AsyncAction = () => void | Promise<void>;
	type NotificationSettingsState = typeof INITIAL_NOTIFICATION_SETTINGS;
	type CarbonSettingsState = typeof INITIAL_CARBON_SETTINGS;
	type LlmSettingsState = typeof INITIAL_LLM_SETTINGS;
	type ActiveOpsSettingsState = typeof INITIAL_ACTIVEOPS_SETTINGS;
	type ProviderModelsState = typeof INITIAL_PROVIDER_MODELS;

	let {
		data,
		loading,
		error,
		success,
		persona = $bindable(),
		savingPersona,
		savePersona,
		carbonSettings = $bindable(),
		loadingCarbon,
		savingCarbon,
		saveCarbonSettings,
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
		loading: boolean;
		error: string;
		success: string;
		persona: string;
		savingPersona: boolean;
		savePersona: AsyncAction;
		carbonSettings: CarbonSettingsState;
		loadingCarbon: boolean;
		savingCarbon: boolean;
		saveCarbonSettings: AsyncAction;
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

	const isGrowthTier = $derived(['growth', 'pro', 'enterprise'].includes(data.subscription?.tier ?? ''));
	const carbonUpgradePrompt = getUpgradePrompt('growth', 'GreenOps controls');
</script>

<div class="space-y-8">
	<div>
		<h1 class="text-2xl font-bold mb-1">Preferences</h1>
		<p class="text-ink-400 text-sm">Configure your notifications, AI strategy, and GreenOps thresholds.</p>
	</div>

	<AuthGate authenticated={!!data.user} action="manage settings">
		{#if loading}
			<div class="card">
				<div class="skeleton h-8 w-48 mb-4"></div>
				<div class="skeleton h-4 w-full mb-2"></div>
				<div class="skeleton h-4 w-3/4"></div>
			</div>
		{:else}
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

			<div class="card stagger-enter">
				<h2 class="text-lg font-semibold mb-2 flex items-center gap-2"><span>🧭</span> Default Persona</h2>
				<p class="text-xs text-ink-400 mb-4">
					Choose which workflows Valdrics prioritizes by default. This does not change access permissions.
				</p>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div class="form-group">
						<label for="persona">Persona</label>
						<select id="persona" bind:value={persona} class="select" aria-label="Default persona">
							<option value="engineering">Engineering (waste + remediation)</option>
							<option value="finance">Finance (allocation + unit economics)</option>
							<option value="platform">Platform (ops + guardrails)</option>
							<option value="leadership">Leadership (high-level drivers)</option>
						</select>
					</div>
					<div class="flex items-end">
						<button
							type="button"
							class="btn btn-primary w-full"
							onclick={savePersona}
							disabled={savingPersona}
							aria-label="Save persona"
						>
							{savingPersona ? '⏳ Saving...' : '💾 Save Persona'}
						</button>
					</div>
				</div>
			</div>

			<div
				class="card stagger-enter relative"
				class:opacity-60={!isGrowthTier}
				class:pointer-events-none={!isGrowthTier}
			>
				<div class="flex items-center justify-between mb-5">
					<h2 class="text-lg font-semibold flex items-center gap-2"><span>🌱</span> Carbon Budget</h2>

					{#if !isGrowthTier}
						<span class="badge badge-warning text-xs">Growth Plan Required</span>
					{/if}
				</div>

				{#if !isGrowthTier}
					<div class="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-ink-950/55 px-6 text-center">
						<div class="max-w-md space-y-3 pointer-events-auto">
							<h3 class="text-lg font-semibold text-white">{carbonUpgradePrompt.heading}</h3>
							<p class="text-sm text-ink-300">{carbonUpgradePrompt.body}</p>
							<p class="text-xs text-ink-500">{carbonUpgradePrompt.footnote}</p>
							<a href={`${base}/billing`} class="btn btn-primary shadow-lg">
								{carbonUpgradePrompt.cta}
							</a>
						</div>
					</div>
				{/if}

				{#if loadingCarbon}
					<div class="skeleton h-4 w-48"></div>
				{:else}
					<div class="space-y-4">
						<div class="form-group">
							<label for="carbon_budget">Monthly Carbon Budget (kg CO₂)</label>
							<input
								type="number"
								id="carbon_budget"
								bind:value={carbonSettings.carbon_budget_kg}
								min="0"
								step="10"
								disabled={!isGrowthTier}
								aria-label="Monthly carbon budget in kilograms"
							/>
							<p class="text-xs text-ink-500 mt-1">Set your monthly carbon footprint limit</p>
						</div>

						<div class="form-group">
							<label for="alert_threshold">Alert Threshold (%)</label>
							<input
								type="number"
								id="alert_threshold"
								bind:value={carbonSettings.alert_threshold_percent}
								min="0"
								max="100"
								disabled={!isGrowthTier}
								aria-label="Carbon alert threshold percentage"
							/>
							<p class="text-xs text-ink-500 mt-1">Warn when usage reaches this percentage of budget</p>
						</div>

						<div class="form-group">
							<label for="default_region">Default AWS Region</label>
							<select
								id="default_region"
								bind:value={carbonSettings.default_region}
								class="select"
								disabled={!isGrowthTier}
								aria-label="Default AWS region for carbon analysis"
							>
								<option value="us-west-2">US West (Oregon) - 21 gCO₂/kWh ⭐</option>
								<option value="eu-north-1">EU (Stockholm) - 28 gCO₂/kWh ⭐</option>
								<option value="ca-central-1">Canada (Central) - 35 gCO₂/kWh ⭐</option>
								<option value="eu-west-1">EU (Ireland) - 316 gCO₂/kWh</option>
								<option value="us-east-1">US East (N. Virginia) - 379 gCO₂/kWh</option>
								<option value="ap-northeast-1">Asia Pacific (Tokyo) - 506 gCO₂/kWh</option>
							</select>
							<p class="text-xs text-ink-500 mt-1">Regions marked with ⭐ have lowest carbon intensity</p>
						</div>

						<div class="form-group">
							<label class="flex items-center gap-3 cursor-pointer">
								<input
									type="checkbox"
									bind:checked={carbonSettings.email_enabled}
									class="toggle"
									disabled={!isGrowthTier}
									aria-label="Enable email notifications for carbon alerts"
								/>
								<span>Enable email notifications for carbon alerts</span>
							</label>
						</div>

						{#if carbonSettings.email_enabled}
							<div class="form-group">
								<label for="email_recipients">Email Recipients</label>
								<input
									type="text"
									id="email_recipients"
									bind:value={carbonSettings.email_recipients}
									placeholder="email1@example.com, email2@example.com"
									disabled={!isGrowthTier}
									aria-label="Carbon alert email recipients"
								/>
								<p class="text-xs text-ink-500 mt-1">
									Comma-separated email addresses for carbon budget alerts
								</p>
							</div>
						{/if}

						<button
							type="button"
							class="btn btn-primary"
							onclick={saveCarbonSettings}
							disabled={savingCarbon || !isGrowthTier}
							aria-label="Save carbon budget settings"
						>
							{savingCarbon ? '⏳ Saving...' : '💾 Save Carbon Settings'}
						</button>
					</div>
				{/if}
			</div>

			<IdentitySettingsCard accessToken={data.session?.access_token} tier={data.subscription?.tier} />
			<EnforcementSettingsCard accessToken={data.session?.access_token} tier={data.subscription?.tier} />
			<EnforcementOpsCard accessToken={data.session?.access_token} tier={data.subscription?.tier} />

			<SettingsAiStrategyCard
				{loadingLLM}
				bind:llmSettings={llmSettings}
				{providerModels}
				{saveLLMSettings}
				{savingLLM}
			/>

			<SettingsActiveOpsCard
				{data}
				{loadingActiveOps}
				bind:activeOpsSettings={activeOpsSettings}
				{saveActiveOpsSettings}
				{savingActiveOps}
			/>

			<SettingsSafetyControlsCard
				{loadingSafety}
				{resettingSafety}
				{loadSafetyStatus}
				{resetSafetyCircuitBreaker}
				{safetyError}
				{safetySuccess}
				{safetyStatus}
			/>

			<SettingsNotificationControls
				{data}
				bind:settings={settings}
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
		{/if}
	</AuthGate>
</div>
