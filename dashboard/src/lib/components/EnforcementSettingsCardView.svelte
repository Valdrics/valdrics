<script lang="ts">
	import { getUpgradePrompt } from '$lib/pricing/upgradePrompt';
	import type {
		EnforcementBudget,
		EnforcementCredit,
		EnforcementPolicy
	} from './enforcementSettingsModel';

	type EnforcementBudgetForm = {
		scope_key: string;
		monthly_limit_usd: number;
		active: boolean;
	};

	type EnforcementCreditForm = {
		scope_key: string;
		total_amount_usd: number;
		expires_at: string;
		reason: string;
	};

	let {
		proPlus,
		billingHref,
		loading,
		savingPolicy,
		savingBudget,
		savingCredit,
		error,
		success,
		policy = $bindable(),
		budgets,
		credits,
		budgetForm = $bindable(),
		creditForm = $bindable(),
		onSavePolicy,
		onUpsertBudget,
		onCreateCredit
	}: {
		proPlus: boolean;
		billingHref: string;
		loading: boolean;
		savingPolicy: boolean;
		savingBudget: boolean;
		savingCredit: boolean;
		error: string;
		success: string;
		policy: EnforcementPolicy;
		budgets: EnforcementBudget[];
		credits: EnforcementCredit[];
		budgetForm: EnforcementBudgetForm;
		creditForm: EnforcementCreditForm;
		onSavePolicy: () => void | Promise<void>;
		onUpsertBudget: () => void | Promise<void>;
		onCreateCredit: () => void | Promise<void>;
	} = $props();

	const upgradePrompt = getUpgradePrompt('pro', 'enforcement controls');
</script>

<div class="card stagger-enter relative" class:opacity-60={!proPlus} class:pointer-events-none={!proPlus}>
	<div class="flex items-center justify-between mb-3">
		<h2 class="text-lg font-semibold flex items-center gap-2">
			<span>🛡️</span> Enforcement Control Plane
		</h2>
		{#if !proPlus}
			<span class="badge badge-warning text-xs">Pro Plan Required</span>
		{/if}
	</div>

	{#if !proPlus}
		<div class="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-ink-950/55 px-6 text-center">
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

			<div class="pt-4 border-t border-ink-700">
				<h3 class="text-sm font-semibold mb-3">Budget Allocations</h3>
				<div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
					<div class="form-group">
						<label for="enforcement_budget_scope">Scope Key</label>
						<input
							id="enforcement_budget_scope"
							bind:value={budgetForm.scope_key}
							aria-label="Enforcement budget scope key"
						/>
					</div>
					<div class="form-group">
						<label for="enforcement_budget_limit">Monthly Limit (USD)</label>
						<input
							type="number"
							id="enforcement_budget_limit"
							min="0"
							step="0.01"
							bind:value={budgetForm.monthly_limit_usd}
							aria-label="Enforcement budget monthly limit"
						/>
					</div>
					<label class="flex items-center gap-3 cursor-pointer mt-7">
						<input
							type="checkbox"
							class="toggle"
							bind:checked={budgetForm.active}
							aria-label="Enforcement budget active"
						/>
						<span>Active</span>
					</label>
				</div>
				<button
					type="button"
					class="btn btn-secondary mb-3"
					onclick={onUpsertBudget}
					disabled={savingBudget}
					aria-label="Save enforcement budget"
				>
					{savingBudget ? '⏳ Saving...' : 'Save Budget'}
				</button>

				{#if budgets.length === 0}
					<p class="text-xs text-ink-500">No budgets configured yet.</p>
				{:else}
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="text-left text-ink-500">
									<th class="py-2">Scope</th>
									<th class="py-2">Monthly Limit</th>
									<th class="py-2">Active</th>
								</tr>
							</thead>
							<tbody>
								{#each budgets as row (row.id)}
									<tr class="border-t border-ink-700">
										<td class="py-2">{row.scope_key}</td>
										<td class="py-2">${Number(row.monthly_limit_usd).toFixed(2)}</td>
										<td class="py-2">{row.active ? 'yes' : 'no'}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</div>

			<div class="pt-4 border-t border-ink-700">
				<h3 class="text-sm font-semibold mb-3">Credits</h3>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
					<div class="form-group">
						<label for="enforcement_credit_scope">Scope Key</label>
						<input
							id="enforcement_credit_scope"
							bind:value={creditForm.scope_key}
							aria-label="Enforcement credit scope key"
						/>
					</div>
					<div class="form-group">
						<label for="enforcement_credit_total">Credit Amount (USD)</label>
						<input
							type="number"
							id="enforcement_credit_total"
							min="0.01"
							step="0.01"
							bind:value={creditForm.total_amount_usd}
							aria-label="Enforcement credit total amount"
						/>
					</div>
					<div class="form-group">
						<label for="enforcement_credit_expiry">Expiry (optional)</label>
						<input
							type="datetime-local"
							id="enforcement_credit_expiry"
							bind:value={creditForm.expires_at}
							aria-label="Enforcement credit expiry"
						/>
					</div>
					<div class="form-group">
						<label for="enforcement_credit_reason">Reason (optional)</label>
						<input
							id="enforcement_credit_reason"
							bind:value={creditForm.reason}
							aria-label="Enforcement credit reason"
						/>
					</div>
				</div>
				<button
					type="button"
					class="btn btn-secondary mb-3"
					onclick={onCreateCredit}
					disabled={savingCredit}
					aria-label="Create enforcement credit"
				>
					{savingCredit ? '⏳ Saving...' : 'Create Credit'}
				</button>

				{#if credits.length === 0}
					<p class="text-xs text-ink-500">No credits available.</p>
				{:else}
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="text-left text-ink-500">
									<th class="py-2">Scope</th>
									<th class="py-2">Remaining</th>
									<th class="py-2">Expires</th>
								</tr>
							</thead>
							<tbody>
								{#each credits as row (row.id)}
									<tr class="border-t border-ink-700">
										<td class="py-2">{row.scope_key}</td>
										<td class="py-2">${Number(row.remaining_amount_usd).toFixed(2)}</td>
										<td class="py-2">
											{row.expires_at ? new Date(row.expires_at).toLocaleString() : 'none'}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
