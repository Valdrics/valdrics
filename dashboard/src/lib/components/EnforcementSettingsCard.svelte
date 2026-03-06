<script lang="ts">
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { TimeoutError } from '$lib/fetchWithTimeout';
	import { z } from 'zod';
	import EnforcementSettingsCardView from './EnforcementSettingsCardView.svelte';
	import {
		createEnforcementCredit,
		loadEnforcementBudgets,
		loadEnforcementCredits,
		loadEnforcementPolicy,
		saveEnforcementBudget,
		saveEnforcementPolicy
	} from './enforcementSettingsApi';
	import {
		PolicySchema,
		isProPlus,
		type EnforcementBudget,
		type EnforcementCredit,
		type EnforcementPolicy
	} from './enforcementSettingsModel';

	let {
		accessToken,
		tier
	}: {
		accessToken?: string | null;
		tier?: string | null;
	} = $props();
	const billingHref = `${base}/billing`;

	let loading = $state(true);
	let savingPolicy = $state(false);
	let savingBudget = $state(false);
	let savingCredit = $state(false);
	let error = $state('');
	let success = $state('');

	let policy = $state<EnforcementPolicy>({
		terraform_mode: 'soft',
		k8s_admission_mode: 'soft',
		require_approval_for_prod: true,
		require_approval_for_nonprod: false,
		auto_approve_below_monthly_usd: 25,
		hard_deny_above_monthly_usd: 5000,
		default_ttl_seconds: 900
	});
	let budgets = $state<EnforcementBudget[]>([]);
	let credits = $state<EnforcementCredit[]>([]);

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

	async function loadPolicy() {
		const loaded = await loadEnforcementPolicy(accessToken);
		if (!loaded) return;
		policy = {
			...policy,
			...loaded,
			auto_approve_below_monthly_usd: Number(loaded.auto_approve_below_monthly_usd ?? 0),
			hard_deny_above_monthly_usd: Number(loaded.hard_deny_above_monthly_usd ?? 0),
			default_ttl_seconds: Number(loaded.default_ttl_seconds ?? 900)
		};
	}

	async function loadBudgets() {
		budgets = await loadEnforcementBudgets(accessToken);
	}

	async function loadCredits() {
		credits = await loadEnforcementCredits(accessToken);
	}

	async function loadAll() {
		loading = true;
		error = '';
		success = '';
		try {
			if (!accessToken || !isProPlus(tier)) return;
			await Promise.all([loadPolicy(), loadBudgets(), loadCredits()]);
		} catch (e) {
			if (e instanceof TimeoutError) {
				error = 'Enforcement settings request timed out. Please retry.';
			} else {
				const err = e as Error;
				error = err.message || 'Failed to load enforcement settings';
			}
		} finally {
			loading = false;
		}
	}

	async function savePolicy() {
		savingPolicy = true;
		error = '';
		success = '';
		try {
			const validated = PolicySchema.parse(policy);
			await saveEnforcementPolicy(accessToken, validated);
			await loadPolicy();
			success = 'Enforcement policy saved.';
		} catch (e) {
			if (e instanceof z.ZodError) {
				error = e.issues.map((issue) => issue.message).join(', ');
			} else {
				const err = e as Error;
				error = err.message || 'Failed to save enforcement policy';
			}
		} finally {
			savingPolicy = false;
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
			await loadBudgets();
			success = 'Enforcement budget saved.';
		} catch (e) {
			const err = e as Error;
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
			await loadCredits();
			success = 'Enforcement credit created.';
		} catch (e) {
			const err = e as Error;
			error = err.message || 'Failed to create enforcement credit';
		} finally {
			savingCredit = false;
		}
	}

	onMount(() => {
		void loadAll();
	});
</script>

<EnforcementSettingsCardView
	proPlus={isProPlus(tier)}
	{billingHref}
	{loading}
	{savingPolicy}
	{savingBudget}
	{savingCredit}
	{error}
	{success}
	{budgets}
	{credits}
	onSavePolicy={savePolicy}
	onUpsertBudget={upsertBudget}
	onCreateCredit={createCredit}
	bind:policy
	bind:budgetForm
	bind:creditForm
/>
