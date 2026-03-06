<!--
  GreenOps Dashboard - Carbon Footprint & Sustainability

  Features:
  - Carbon footprint tracking (Scope 2 + Scope 3)
  - Carbon efficiency score
  - Green region recommendations
  - Graviton migration opportunities
  - Carbon budget monitoring
-->

<script lang="ts">
	/* eslint-disable svelte/no-navigation-without-resolve */
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import AuthGate from '$lib/components/AuthGate.svelte';
	import { edgeApiPath } from '$lib/edgeProxy';
	import { TimeoutError, fetchWithTimeout } from '$lib/fetchWithTimeout';
	import GreenOpsTierPreview from './GreenOpsTierPreview.svelte';
	import GreenOpsMetricsGrid from './GreenOpsMetricsGrid.svelte';
	import GreenOpsRecommendationsSchedule from './GreenOpsRecommendationsSchedule.svelte';
	import type {
		BudgetData,
		CarbonData,
		GravitonData,
		IntensityData,
		ScheduleResult
	} from './greenopsTypes';

	let { data } = $props();

	const GREENOPS_TIMEOUT_MS = 10000;
	let carbonData = $state<CarbonData | null>(null);
	let gravitonData = $state<GravitonData | null>(null);
	let budgetData = $state<BudgetData | null>(null);
	let intensityData = $state<IntensityData | null>(null);
	let selectedRegion = $derived(data.selectedRegion || 'us-east-1');
	let error = $state('');
	let loading = $state(false);
	let workloadDuration = $state(1);
	let scheduleResult = $state<ScheduleResult | null>(null);
	let greenopsRequestId = 0;

	function toAppPath(path: string): string {
		const normalizedPath = path.startsWith('/') ? path : `/${path}`;
		const normalizedBase = base === '/' ? '' : base;
		return `${normalizedBase}${normalizedPath}`;
	}

	async function loadGreenOpsData(
		region: string,
		accessToken: string | undefined,
		hasUser: boolean
	) {
		const requestId = ++greenopsRequestId;

		if (!hasUser || !accessToken) {
			carbonData = null;
			gravitonData = null;
			budgetData = null;
			intensityData = null;
			error = '';
			loading = false;
			return;
		}

		loading = true;
		error = '';

		try {
			const today = new Date();
			const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
			const startDate = thirtyDaysAgo.toISOString().split('T')[0];
			const endDate = today.toISOString().split('T')[0];
			const headers = { Authorization: `Bearer ${accessToken}` };

			const [carbonRes, gravitonRes, budgetRes, intensityRes] = await Promise.all([
				fetchWithTimeout(
					fetch,
					edgeApiPath(`/carbon?start_date=${startDate}&end_date=${endDate}&region=${region}`),
					{ headers },
					GREENOPS_TIMEOUT_MS
				),
				fetchWithTimeout(
					fetch,
					edgeApiPath(`/carbon/graviton?region=${region}`),
					{ headers },
					GREENOPS_TIMEOUT_MS
				),
				fetchWithTimeout(
					fetch,
					edgeApiPath(`/carbon/budget?region=${region}`),
					{ headers },
					GREENOPS_TIMEOUT_MS
				),
				fetchWithTimeout(
					fetch,
					edgeApiPath(`/carbon/intensity?region=${region}&hours=24`),
					{ headers },
					GREENOPS_TIMEOUT_MS
				)
			]);

			if (requestId !== greenopsRequestId) return;

			carbonData = carbonRes.ok ? await carbonRes.json() : null;
			gravitonData = gravitonRes.ok ? await gravitonRes.json() : null;
			budgetData = budgetRes.ok ? await budgetRes.json() : null;
			intensityData = intensityRes.ok ? await intensityRes.json() : null;

			if (!carbonRes.ok && carbonRes.status === 401) {
				error = 'Session expired. Please refresh the page.';
			} else if (!carbonRes.ok) {
				error = `Failed to fetch carbon data (HTTP ${carbonRes.status}).`;
			} else {
				error = '';
			}
		} catch (err) {
			if (requestId !== greenopsRequestId) return;
			carbonData = null;
			gravitonData = null;
			budgetData = null;
			intensityData = null;
			error =
				err instanceof TimeoutError
					? 'GreenOps data request timed out. Please try again.'
					: 'Network error fetching sustainability data';
		} finally {
			if (requestId === greenopsRequestId) {
				loading = false;
			}
		}
	}

	async function getOptimalSchedule() {
		const res = await api.get(
			edgeApiPath(`/carbon/schedule?region=${selectedRegion}&duration_hours=${workloadDuration}`)
		);
		if (res.ok) {
			scheduleResult = await res.json();
		}
	}

	function handleRegionChange(e: Event) {
		const target = e.target as HTMLSelectElement;
		goto(`${toAppPath('/greenops')}?region=${target.value}`, { keepFocus: true, noScroll: true });
	}

	function formatCO2(kg: number): string {
		if (kg < 1) return `${(kg * 1000).toFixed(1)} g`;
		if (kg < 1000) return `${kg.toFixed(2)} kg`;
		return `${(kg / 1000).toFixed(2)} t`;
	}

	$effect(() => {
		const accessToken = data.session?.access_token;
		const hasUser = !!data.user;
		void loadGreenOpsData(selectedRegion, accessToken, hasUser);
	});
</script>

<svelte:head>
	<title>GreenOps - Valdrics</title>
</svelte:head>

<div class="space-y-6">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold text-white">🌱 GreenOps Dashboard</h1>
			<p class="text-ink-400 mt-1">Monitor your cloud carbon footprint and sustainability</p>
		</div>

		<select
			value={selectedRegion}
			onchange={handleRegionChange}
			class="bg-ink-800 border border-ink-700 rounded-lg px-3 py-2 text-sm"
			aria-label="Select AWS region for carbon analysis"
		>
			<option value="us-east-1">US East (N. Virginia)</option>
			<option value="us-west-2">US West (Oregon)</option>
			<option value="eu-west-1">EU (Ireland)</option>
			<option value="eu-north-1">EU (Stockholm)</option>
			<option value="ap-northeast-1">Asia Pacific (Tokyo)</option>
		</select>
	</div>

	<AuthGate authenticated={!!data.user} action="view GreenOps">
		{#if loading}
			<div class="flex items-center justify-center py-20">
				<div class="animate-spin rounded-full h-8 w-8 border-t-2 border-accent-500"></div>
			</div>
		{:else if !['growth', 'pro', 'enterprise', 'free'].includes(data.subscription?.tier)}
			<GreenOpsTierPreview {toAppPath} />
		{:else if error}
			<div class="card bg-red-900/20 border-red-800 p-6">
				<p class="text-red-400">{error}</p>
			</div>
		{:else}
			<GreenOpsMetricsGrid {carbonData} {gravitonData} {budgetData} {formatCO2} />
			<GreenOpsRecommendationsSchedule
				{carbonData}
				{intensityData}
				bind:workloadDuration
				{scheduleResult}
				onGetOptimalSchedule={getOptimalSchedule}
			/>
		{/if}
	</AuthGate>
</div>
