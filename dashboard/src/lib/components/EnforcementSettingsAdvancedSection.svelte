<script lang="ts">
	import { onMount } from 'svelte';
	import {
		createEnforcementCredit,
		loadEnforcementBudgets,
		loadEnforcementCredits,
		saveEnforcementBudget
	} from './enforcementSettingsApi';
	import type { EnforcementBudget, EnforcementCredit } from './enforcementSettingsModel';

	let { accessToken }: { accessToken?: string | null } = $props();

	let budgets = $state<EnforcementBudget[]>([]);
	let credits = $state<EnforcementCredit[]>([]);
	let loading = $state(true);
	let savingBudget = $state(false);
	let savingCredit = $state(false);
	let error = $state('');
	let success = $state('');

	let budgetForm = $state({
		scope_key: 'default',
		monthly_limit_usd: 0,
		active: true
	});

	let creditForm = $state({
		scope_key: 'default',
		total_amount_usd: 0,
		expires_at: '',
		reason: ''
	});

	async function loadAdvancedState() {
		loading = true;
		error = '';
		success = '';
		try {
			if (!accessToken) {
				budgets = [];
				credits = [];
				return;
			}
			const [nextBudgets, nextCredits] = await Promise.all([
				loadEnforcementBudgets(accessToken),
				loadEnforcementCredits(accessToken)
			]);
			budgets = nextBudgets;
			credits = nextCredits;
		} catch (nextError) {
			const err = nextError as Error;
			error = err.message || 'Failed to load budget and credit controls';
		} finally {
			loading = false;
		}
	}

	async function upsertBudget() {
		savingBudget = true;
		error = '';
		success = '';
		try {
			const payload = {
				scope_key: budgetForm.scope_key.trim() || 'default',
				monthly_limit_usd: Number(budgetForm.monthly_limit_usd),
				active: budgetForm.active
			};
			await saveEnforcementBudget(accessToken, payload);
			await loadAdvancedState();
			success = 'Enforcement budget saved.';
		} catch (nextError) {
			const err = nextError as Error;
			error = err.message || 'Failed to save enforcement budget';
		} finally {
			savingBudget = false;
		}
	}

	async function createCredit() {
		savingCredit = true;
		error = '';
		success = '';
		try {
			const payload = {
				scope_key: creditForm.scope_key.trim() || 'default',
				total_amount_usd: Number(creditForm.total_amount_usd),
				expires_at: creditForm.expires_at ? new Date(creditForm.expires_at).toISOString() : null,
				reason: creditForm.reason.trim() || null
			};
			await createEnforcementCredit(accessToken, payload);
			creditForm = {
				scope_key: creditForm.scope_key,
				total_amount_usd: 0,
				expires_at: '',
				reason: ''
			};
			await loadAdvancedState();
			success = 'Enforcement credit created.';
		} catch (nextError) {
			const err = nextError as Error;
			error = err.message || 'Failed to create enforcement credit';
		} finally {
			savingCredit = false;
		}
	}

	onMount(() => {
		void loadAdvancedState();
	});
</script>

<div class="space-y-6">
	{#if error}
		<div role="alert" class="card border-danger-500/50 bg-danger-500/10">
			<p class="text-danger-400 text-sm">{error}</p>
		</div>
	{/if}

	{#if success}
		<div role="status" class="card border-success-500/50 bg-success-500/10">
			<p class="text-success-400 text-sm">{success}</p>
		</div>
	{/if}

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
			onclick={upsertBudget}
			disabled={savingBudget}
			aria-label="Save enforcement budget"
		>
			{savingBudget ? '⏳ Saving...' : 'Save Budget'}
		</button>

		{#if loading}
			<div class="skeleton h-4 w-48"></div>
		{:else if budgets.length === 0}
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
			onclick={createCredit}
			disabled={savingCredit}
			aria-label="Create enforcement credit"
		>
			{savingCredit ? '⏳ Saving...' : 'Create Credit'}
		</button>

		{#if loading}
			<div class="skeleton h-4 w-48"></div>
		{:else if credits.length === 0}
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
