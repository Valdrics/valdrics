<script lang="ts">
	import { base } from '$app/paths';
	import { getUpgradePrompt } from '$lib/pricing/upgradePrompt';
	import { tierAtLeast } from '$lib/tier';
	import { INITIAL_ACTIVEOPS_SETTINGS } from './settingsPageInitialState';

	type AsyncAction = () => void | Promise<void>;
	type ActiveOpsSettingsState = typeof INITIAL_ACTIVEOPS_SETTINGS;

	interface Props {
		data: {
			subscription?: {
				tier?: string;
			};
		};
		loadingActiveOps: boolean;
		activeOpsSettings: ActiveOpsSettingsState;
		saveActiveOpsSettings: AsyncAction;
		savingActiveOps: boolean;
	}

	let {
		data,
		loadingActiveOps,
		activeOpsSettings = $bindable(),
		saveActiveOpsSettings,
		savingActiveOps
	}: Props = $props();

	const hasProAutomationAccess = $derived(tierAtLeast(data.subscription?.tier ?? 'free', 'pro'));
	const upgradePrompt = getUpgradePrompt('pro', 'ActiveOps automation');
</script>

<!-- ActiveOps (Remediation) Settings -->
<div
	class="card stagger-enter relative"
	class:opacity-60={!hasProAutomationAccess}
	class:pointer-events-none={!hasProAutomationAccess}
>
	<div class="flex items-center justify-between mb-3">
		<h2 class="text-lg font-semibold flex items-center gap-2">
			<span>⚡</span> ActiveOps (Autonomous Remediation)
		</h2>

		{#if !hasProAutomationAccess}
			<span class="badge badge-warning text-xs">Pro Plan Required</span>
		{/if}
	</div>

	{#if !hasProAutomationAccess}
		<div class="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-ink-950/55 px-6 text-center">
			<div class="max-w-md space-y-3 pointer-events-auto">
				<h3 class="text-lg font-semibold text-white">{upgradePrompt.heading}</h3>
				<p class="text-sm text-ink-300">{upgradePrompt.body}</p>
				<p class="text-xs text-ink-500">{upgradePrompt.footnote}</p>
				<a href={`${base}/billing`} class="btn btn-primary shadow-lg">{upgradePrompt.cta}</a>
			</div>
		</div>
	{/if}

	<p class="text-xs text-ink-400 mb-5">
		ActiveOps automation stays on Pro and Enterprise. Slack and Jira switches in this card apply
		to remediation policy events, not the general notification channel.
	</p>

	{#if loadingActiveOps}
		<div class="skeleton h-4 w-48"></div>
	{:else}
		<div class="space-y-6">
			<div class="p-4 rounded-lg bg-warning-900/10 border border-warning-900/30">
				<h4 class="text-sm font-bold text-warning-400 mb-1">⚠️ Safety Disclaimer</h4>
				<p class="text-xs text-warning-500 leading-relaxed">
					Auto-Pilot mode allows Valdrics to perform destructive actions (deletion) on identified
					resources. Always ensure you have regular backups. Actions are only taken if the AI
					confidence exceeds the specified threshold.
				</p>
			</div>

			<label class="flex items-center gap-3 cursor-pointer">
				<input
					type="checkbox"
					bind:checked={activeOpsSettings.auto_pilot_enabled}
					class="toggle toggle-warning"
					disabled={!hasProAutomationAccess}
					aria-label="Enable Auto-Pilot for autonomous deletion"
				/>
				<span class="font-medium {activeOpsSettings.auto_pilot_enabled ? 'text-white' : 'text-ink-400'}">
					Enable Auto-Pilot (Weekly Autonomous Deletion)
				</span>
			</label>

			<div class="form-group">
				<label for="confidence_threshold"
					>Min Confidence Threshold: {Math.round(activeOpsSettings.min_confidence_threshold * 100)}%</label
				>
				<input
					type="range"
					id="confidence_threshold"
					bind:value={activeOpsSettings.min_confidence_threshold}
					min="0.5"
					max="1.0"
					step="0.01"
					class="range"
					disabled={!activeOpsSettings.auto_pilot_enabled ||
						!hasProAutomationAccess}
					aria-label="Minimum AI confidence threshold for autonomous actions"
				/>
				<div class="flex justify-between text-xs text-ink-500 mt-1">
					<span>Riskier (50%)</span>
					<span>Ultra-Safe (100%)</span>
				</div>
			</div>

			<div class="pt-2 border-t border-white/10 space-y-3">
				<h4 class="text-sm font-semibold text-ink-200">Policy Guardrails</h4>
				<label class="flex items-center gap-3 cursor-pointer">
					<input
						type="checkbox"
						bind:checked={activeOpsSettings.policy_enabled}
						class="toggle"
						disabled={!hasProAutomationAccess}
					/>
					<span>Enable request-level policy guardrails</span>
				</label>

				<label class="flex items-center gap-3 cursor-pointer">
					<input
						type="checkbox"
						bind:checked={activeOpsSettings.policy_block_production_destructive}
						class="toggle"
						disabled={!activeOpsSettings.policy_enabled ||
							!hasProAutomationAccess}
					/>
					<span>Block destructive actions on production-like resources</span>
				</label>

				<label class="flex items-center gap-3 cursor-pointer">
					<input
						type="checkbox"
						bind:checked={activeOpsSettings.policy_require_gpu_override}
						class="toggle"
						disabled={!activeOpsSettings.policy_enabled ||
							!hasProAutomationAccess}
					/>
					<span>Require explicit override for GPU-impacting changes</span>
				</label>

				<div class="form-group">
					<label for="policy_warn_threshold"
						>Low-Confidence Warn Threshold: {Math.round(
							activeOpsSettings.policy_low_confidence_warn_threshold * 100
						)}%</label
					>
					<input
						type="range"
						id="policy_warn_threshold"
						bind:value={activeOpsSettings.policy_low_confidence_warn_threshold}
						min="0.5"
						max="1.0"
						step="0.01"
						class="range"
						disabled={!activeOpsSettings.policy_enabled ||
							!hasProAutomationAccess}
					/>
				</div>

				<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
					<label class="flex items-center gap-3 cursor-pointer">
						<input
							type="checkbox"
							bind:checked={activeOpsSettings.policy_violation_notify_slack}
							class="toggle"
							disabled={!activeOpsSettings.policy_enabled ||
								!hasProAutomationAccess}
						/>
						<span>Notify policy violations to Slack</span>
					</label>
					<label class="flex items-center gap-3 cursor-pointer">
						<input
							type="checkbox"
							bind:checked={activeOpsSettings.policy_violation_notify_jira}
							class="toggle"
							disabled={!activeOpsSettings.policy_enabled ||
								!hasProAutomationAccess}
						/>
						<span>Notify policy violations to Jira</span>
					</label>
				</div>

				<div class="form-group border-t border-white/10 pt-4">
					<label for="policy_escalation_role">Escalation Approval Role</label>
					<select
						id="policy_escalation_role"
						bind:value={activeOpsSettings.policy_escalation_required_role}
						disabled={!activeOpsSettings.policy_enabled ||
							!hasProAutomationAccess}
					>
						<option value="owner">Owner</option>
						<option value="admin">Admin</option>
					</select>
				</div>
			</div>

			<div class="pt-2 border-t border-white/10 space-y-4">
				<h4 class="text-sm font-semibold text-ink-200 flex items-center gap-2">
					<span>🪪</span> License & SaaS Governance
				</h4>

				<label class="flex items-center gap-3 cursor-pointer">
					<input
					type="checkbox"
					bind:checked={activeOpsSettings.license_auto_reclaim_enabled}
					class="toggle toggle-success"
					disabled={!hasProAutomationAccess}
				/>
					<span>Enable autonomous seat reclamation for inactive users</span>
				</label>

				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div class="form-group">
						<label for="inactive_threshold"
							>Inactivity Threshold: {activeOpsSettings.license_inactive_threshold_days} days</label
						>
						<input
							type="range"
							id="inactive_threshold"
							bind:value={activeOpsSettings.license_inactive_threshold_days}
							min="7"
							max="365"
							step="1"
							class="range range-success"
							disabled={!activeOpsSettings.license_auto_reclaim_enabled}
						/>
					</div>
					<div class="form-group">
						<label for="grace_period"
							>Notification Grace Period: {activeOpsSettings.license_reclaim_grace_period_days}
							days</label
						>
						<input
							type="range"
							id="grace_period"
							bind:value={activeOpsSettings.license_reclaim_grace_period_days}
							min="1"
							max="30"
							step="1"
							class="range range-info"
							disabled={!activeOpsSettings.license_auto_reclaim_enabled}
						/>
					</div>
				</div>

				<label class="flex items-center gap-3 cursor-pointer">
					<input
					type="checkbox"
					bind:checked={activeOpsSettings.license_downgrade_recommendations_enabled}
					class="toggle"
					disabled={!hasProAutomationAccess}
				/>
					<span>Enable cost-saving tier downgrade recommendations</span>
				</label>
			</div>

			<button
				type="button"
				class="btn btn-primary"
				onclick={saveActiveOpsSettings}
				disabled={savingActiveOps || !hasProAutomationAccess}
				aria-label="Save ActiveOps settings"
			>
				{savingActiveOps ? '⏳ Saving...' : '💾 Save ActiveOps Settings'}
			</button>
		</div>
	{/if}
</div>
