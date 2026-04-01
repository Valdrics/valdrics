<script lang="ts">
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { TimeoutError } from '$lib/fetchWithTimeout';
	import { formatValidationIssues } from '$lib/validation/clientZod';
	import EnforcementSettingsCardView from './EnforcementSettingsCardView.svelte';
	import { loadEnforcementPolicy, saveEnforcementPolicy } from './enforcementSettingsApi';
	import { PolicySchema, isProPlus, type EnforcementPolicy } from './enforcementSettingsModel';

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

	async function loadAll() {
		loading = true;
		error = '';
		success = '';
		try {
			if (!accessToken || !isProPlus(tier)) return;
			await loadPolicy();
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
			error = formatValidationIssues(e, false) || 'Failed to save enforcement policy';
		} finally {
			savingPolicy = false;
		}
	}

	onMount(() => {
		void loadAll();
	});
</script>

<EnforcementSettingsCardView
	{accessToken}
	proPlus={isProPlus(tier)}
	{billingHref}
	{loading}
	{savingPolicy}
	{error}
	{success}
	onSavePolicy={savePolicy}
	bind:policy
/>
