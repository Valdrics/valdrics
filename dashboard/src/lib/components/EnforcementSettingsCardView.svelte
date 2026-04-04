<script lang="ts">
	import { onMount } from 'svelte';
	import { createLazyComponent } from '$lib/lazyComponent';
	import { getUpgradePrompt } from '$lib/pricing/upgradePrompt';
	import type { EnforcementPolicy } from './enforcementSettingsModel';

	let {
		accessToken,
		proPlus,
		billingHref,
		loading,
		savingPolicy,
		error,
		success,
		policy = $bindable(),
		onSavePolicy
	}: {
		accessToken?: string | null;
		proPlus: boolean;
		billingHref: string;
		loading: boolean;
		savingPolicy: boolean;
		error: string;
		success: string;
		policy: EnforcementPolicy;
		onSavePolicy: () => void | Promise<void>;
	} = $props();

	type EnforcementSettingsAdvancedSectionProps = {
		accessToken?: string | null;
	};

	const loadEnforcementSettingsAdvancedSection =
		createLazyComponent<EnforcementSettingsAdvancedSectionProps>(
			() => import('./EnforcementSettingsAdvancedSection.svelte')
		);

	const upgradePrompt = getUpgradePrompt('pro', 'enforcement controls');

	let advancedSectionAnchor = $state<HTMLDivElement | null>(null);
	let advancedSectionReady = $state(import.meta.env.MODE === 'test');

	onMount(() => {
		if (advancedSectionReady || typeof IntersectionObserver === 'undefined') {
			advancedSectionReady = true;
			return;
		}

		const observer = new IntersectionObserver(
			(entries) => {
				if (entries.some((entry) => entry.isIntersecting)) {
					advancedSectionReady = true;
					observer.disconnect();
				}
			},
			{ rootMargin: '280px 0px' }
		);

		if (advancedSectionAnchor) {
			observer.observe(advancedSectionAnchor);
		}

		return () => observer.disconnect();
	});
</script>

<div
	class="card stagger-enter relative"
	class:opacity-60={!proPlus}
	class:pointer-events-none={!proPlus}
>
	<div class="flex items-center justify-between mb-3">
		<h2 class="text-lg font-semibold flex items-center gap-2">
			<span>🛡️</span> Enforcement Control Plane
		</h2>
		{#if !proPlus}
			<span class="badge badge-warning text-xs">Pro Plan Required</span>
		{/if}
	</div>

	{#if !proPlus}
		<div
			class="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-ink-950/55 px-6 text-center"
		>
			<div class="max-w-md space-y-3 pointer-events-auto">
				<h3 class="text-lg font-semibold text-white">{upgradePrompt.heading}</h3>
				<p class="text-sm text-ink-300">{upgradePrompt.body}</p>
				<p class="text-xs text-ink-500">{upgradePrompt.footnote}</p>
				<a href={billingHref} class="btn btn-primary shadow-lg">{upgradePrompt.cta}</a>
			</div>
		</div>
	{/if}

	<p class="text-xs text-ink-400 mb-5">
		Configure pre-provision gate policy, monthly budget envelopes, and temporary enforcement
		credits.
	</p>

	{#if error}
		<div role="alert" class="card border-danger-500/50 bg-danger-500/10 mb-4">
			<p class="text-danger-400 text-sm">{error}</p>
		</div>
	{/if}

	{#if success}
		<div role="status" class="card border-success-500/50 bg-success-500/10 mb-4">
			<p class="text-success-400 text-sm">{success}</p>
		</div>
	{/if}

	{#if loading}
		<div class="skeleton h-4 w-64"></div>
	{:else}
		<div class="space-y-6">
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div class="form-group">
					<label for="enforcement_terraform_mode">Terraform Gate Mode</label>
					<select
						id="enforcement_terraform_mode"
						class="select"
						bind:value={policy.terraform_mode}
						aria-label="Terraform gate mode"
					>
						<option value="shadow">shadow</option>
						<option value="soft">soft</option>
						<option value="hard">hard</option>
					</select>
				</div>
				<div class="form-group">
					<label for="enforcement_k8s_mode">K8s Admission Mode</label>
					<select
						id="enforcement_k8s_mode"
						class="select"
						bind:value={policy.k8s_admission_mode}
						aria-label="Kubernetes admission mode"
					>
						<option value="shadow">shadow</option>
						<option value="soft">soft</option>
						<option value="hard">hard</option>
					</select>
				</div>
			</div>

			<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
				<div class="form-group">
					<label for="enforcement_auto_approve_threshold">Auto-Approve Below (USD/month)</label>
					<input
						type="number"
						id="enforcement_auto_approve_threshold"
						min="0"
						step="0.01"
						bind:value={policy.auto_approve_below_monthly_usd}
						aria-label="Auto approve threshold per month"
					/>
				</div>
				<div class="form-group">
					<label for="enforcement_hard_deny_threshold">Hard-Deny Above (USD/month)</label>
					<input
						type="number"
						id="enforcement_hard_deny_threshold"
						min="0.01"
						step="0.01"
						bind:value={policy.hard_deny_above_monthly_usd}
						aria-label="Hard deny threshold per month"
					/>
				</div>
				<div class="form-group">
					<label for="enforcement_ttl_seconds">Approval TTL (seconds)</label>
					<input
						type="number"
						id="enforcement_ttl_seconds"
						min="60"
						max="86400"
						step="1"
						bind:value={policy.default_ttl_seconds}
						aria-label="Approval TTL in seconds"
					/>
				</div>
			</div>

			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<label class="flex items-center gap-3 cursor-pointer">
					<input
						type="checkbox"
						class="toggle"
						bind:checked={policy.require_approval_for_prod}
						aria-label="Require approval for prod"
					/>
					<span>Require approval for prod</span>
				</label>
				<label class="flex items-center gap-3 cursor-pointer">
					<input
						type="checkbox"
						class="toggle"
						bind:checked={policy.require_approval_for_nonprod}
						aria-label="Require approval for nonprod"
					/>
					<span>Require approval for non-prod</span>
				</label>
			</div>

			<div class="flex flex-wrap gap-3 items-center">
				<button
					type="button"
					class="btn btn-primary"
					onclick={onSavePolicy}
					disabled={savingPolicy}
					aria-label="Save enforcement policy"
				>
					{savingPolicy ? '⏳ Saving...' : '💾 Save Enforcement Policy'}
				</button>
				{#if policy.policy_version}
					<span class="text-xs text-ink-500">
						Policy v{policy.policy_version}{policy.updated_at
							? ` • updated ${new Date(policy.updated_at).toLocaleString()}`
							: ''}
					</span>
				{/if}
			</div>

			<div bind:this={advancedSectionAnchor}>
				{#if advancedSectionReady}
					{#await loadEnforcementSettingsAdvancedSection()}
						<div class="pt-4 border-t border-ink-700 space-y-4">
							<div class="skeleton h-4 w-40"></div>
							<div class="skeleton h-4 w-full"></div>
							<div class="skeleton h-4 w-2/3"></div>
						</div>
					{:then module}
						{@const EnforcementSettingsAdvancedSection = module.default}
						<EnforcementSettingsAdvancedSection {accessToken} />
					{:catch}
						<div class="pt-4 border-t border-ink-700">
							<p class="text-xs text-ink-500">
								Budget and credit controls are temporarily unavailable.
							</p>
						</div>
					{/await}
				{:else}
					<div class="pt-4 border-t border-ink-700 space-y-4">
						<div class="skeleton h-4 w-40"></div>
						<div class="skeleton h-4 w-full"></div>
						<div class="skeleton h-4 w-2/3"></div>
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
