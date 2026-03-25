<script lang="ts">
	/* eslint-disable svelte/no-navigation-without-resolve */
	import './dashboard.app.css';
	import { base } from '$app/paths';
	import { AlertTriangle, Clock } from '@lucide/svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onDestroy } from 'svelte';
	import AuthGate from '$lib/components/AuthGate.svelte';
	import { resolveSessionTenantId } from '$lib/auth/sessionTenant';
	import { trackProductFunnelStage } from '$lib/funnel/productFunnelTelemetry';
	import DateRangePicker from '$lib/components/DateRangePicker.svelte';
	import ProviderSelector from '$lib/components/ProviderSelector.svelte';
	import StatsGrid from '$lib/components/StatsGrid.svelte';
	import { createLazyComponent } from '$lib/lazyComponent';
	import { countZombieFindings, type ZombieCollections } from '$lib/zombieCollections';
	import { getDashboardPersonaContent } from '../homeDashboardContent';

	type RemediationFinding = {
		finding_id?: string;
		resource_id: string;
		resource_type?: string;
		provider?: string;
		connection_id?: string;
		monthly_cost?: string | number;
		recommended_action?: string;
		owner?: string;
		explainability_notes?: string;
		confidence_score?: number;
		db_class?: string;
		lb_type?: string;
		is_gpu?: boolean;
		instance_type?: string;
	};

	const loadEngineeringDashboardSection = createLazyComponent(
		() => import('./EngineeringDashboardSection.svelte')
	);
	const loadFinanceDashboardSection = createLazyComponent(
		() => import('./FinanceDashboardSection.svelte')
	);
	const loadRemediationModal = createLazyComponent(
		() => import('$lib/components/RemediationModal.svelte')
	);

	type EngineeringDashboardSectionComponent = Awaited<
		ReturnType<typeof loadEngineeringDashboardSection>
	>['default'];
	type FinanceDashboardSectionComponent = Awaited<
		ReturnType<typeof loadFinanceDashboardSection>
	>['default'];
	type RemediationModalComponent = Awaited<ReturnType<typeof loadRemediationModal>>['default'];

	let { data } = $props();

	let costs = $derived(data.costs);
	let carbon = $derived(data.carbon);
	let zombies = $derived(data.zombies);
	let analysis = $derived(data.analysis as { analysis?: string } | null);
	let allocation = $derived(data.allocation);
	let unitEconomics = $derived(data.unitEconomics);
	let freshness = $derived(data.freshness);
	let error = $derived(data.error || '');
	let startDate = $derived(data.startDate || '');
	let endDate = $derived(data.endDate || '');
	let provider = $derived(data.provider || ''); // Default to empty (All)
	let persona = $derived(String(data.profile?.persona ?? 'engineering').toLowerCase());
	let tier = $derived(data.subscription?.tier ?? 'free');
	let tenantId = $derived(resolveSessionTenantId({ session: data.session, user: data.user }));
	let personaContent = $derived(getDashboardPersonaContent(persona));
	// Remediation state
	let remediationCandidate = $state<RemediationFinding | null>(null);
	let remediationModalOpen = $state(false);
	let engineeringDashboardSection = $state<EngineeringDashboardSectionComponent | null>(null);
	let engineeringDashboardSectionError = $state('');
	let financeDashboardSection = $state<FinanceDashboardSectionComponent | null>(null);
	let financeDashboardSectionError = $state('');
	let remediationModalComponent = $state<RemediationModalComponent | null>(null);
	let remediationModalError = $state('');
	let pendingNavigationTimeout = $state<ReturnType<typeof setTimeout> | null>(null);
	let firstValueTracked = $state(false);

	const DASHBOARD_NAV_DEBOUNCE_MS = 300;
	const DASHBOARD_PATH = `${base}/dashboard`;

	function scheduleNavigation(targetPath: string) {
		if (pendingNavigationTimeout) {
			clearTimeout(pendingNavigationTimeout);
		}

		pendingNavigationTimeout = setTimeout(() => {
			void goto(targetPath, {
				keepFocus: true,
				noScroll: true,
				replaceState: true
			});
			pendingNavigationTimeout = null;
		}, DASHBOARD_NAV_DEBOUNCE_MS);
	}

	onDestroy(() => {
		if (pendingNavigationTimeout) {
			clearTimeout(pendingNavigationTimeout);
			pendingNavigationTimeout = null;
		}
	});

	function handleRemediate(finding: RemediationFinding) {
		remediationCandidate = finding;
		remediationModalOpen = true;
		void ensureRemediationModal();
	}

	async function ensureEngineeringDashboardSection() {
		if (engineeringDashboardSection) {
			return;
		}
		try {
			engineeringDashboardSection = (await loadEngineeringDashboardSection()).default;
			engineeringDashboardSectionError = '';
		} catch {
			engineeringDashboardSectionError = 'Unable to load engineering insights right now.';
		}
	}

	async function ensureFinanceDashboardSection() {
		if (financeDashboardSection) {
			return;
		}
		try {
			financeDashboardSection = (await loadFinanceDashboardSection()).default;
			financeDashboardSectionError = '';
		} catch {
			financeDashboardSectionError = 'Unable to load finance insights right now.';
		}
	}

	async function ensureRemediationModal() {
		if (remediationModalComponent) {
			return;
		}
		try {
			remediationModalComponent = (await loadRemediationModal()).default;
			remediationModalError = '';
		} catch {
			remediationModalError = 'Unable to load the remediation workflow.';
		}
	}

	function handleDateChange(dates: { startDate: string; endDate: string }) {
		if (dates.startDate === startDate && dates.endDate === endDate) return;
		const params = new URLSearchParams({
			start_date: dates.startDate,
			end_date: dates.endDate
		});
		if (provider) {
			params.set('provider', provider);
		}
		scheduleNavigation(`${DASHBOARD_PATH}?${params.toString()}`);
	}

	function handleProviderChange(selectedProvider: string) {
		if (selectedProvider === provider) return;

		const params = new URLSearchParams();
		if (startDate && endDate) {
			params.set('start_date', startDate);
			params.set('end_date', endDate);
		}
		if (selectedProvider) {
			params.set('provider', selectedProvider);
		}
		const query = params.toString();
		const targetPath = query.length > 0 ? `${DASHBOARD_PATH}?${query}` : DASHBOARD_PATH;

		scheduleNavigation(targetPath);
	}

	let zombieCount = $derived(countZombieFindings(zombies as ZombieCollections | null | undefined));

	let analysisText = $derived(analysis?.analysis ?? '');

	const hasFirstValueSignal = $derived(
		Boolean(
			!error &&
			data.user &&
			(costs !== null ||
				carbon !== null ||
				zombies !== null ||
				allocation !== null ||
				unitEconomics !== null ||
				freshness !== null)
		)
	);

	$effect(() => {
		if (firstValueTracked || !hasFirstValueSignal || !data.session?.access_token) {
			return;
		}
		firstValueTracked = true;
		void trackProductFunnelStage({
			accessToken: data.session.access_token,
			stage: 'first_value_activated',
			tenantId,
			url: $page.url,
			currentTier: data.subscription?.tier,
			persona: String(data.profile?.persona ?? ''),
			source: 'dashboard_first_value'
		});
	});

	// Calculate period label from dates
	let periodLabel = $derived(
		(() => {
			if (!startDate || !endDate) return 'Period';
			const start = new Date(startDate);
			const end = new Date(endDate);
			const days = Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
			if (days <= 7) return '7-Day';
			if (days <= 30) return '30-Day';
			if (days <= 90) return '90-Day';
			return `${days}-Day`;
		})()
	);

	$effect(() => {
		if (persona === 'engineering') {
			void ensureEngineeringDashboardSection();
		}
	});

	$effect(() => {
		if (persona === 'finance' || persona === 'leadership') {
			void ensureFinanceDashboardSection();
		}
	});
</script>

<svelte:head>
	<title>Dashboard | Valdrics</title>
</svelte:head>

<AuthGate authenticated={!!data.user} action="view the dashboard">
	<div class="space-y-8">
		<!-- Page Header with Date Range Picker -->
		<div class="flex flex-col gap-4">
			<div class="flex items-center justify-between">
				<div>
					<h1 class="text-2xl font-bold mb-1">{personaContent.title} Dashboard</h1>
					<p class="text-ink-400 text-sm">{personaContent.subtitle}</p>
				</div>

				<!-- Provider Selector -->
				<ProviderSelector selectedProvider={provider} onSelect={handleProviderChange} />
			</div>

			<DateRangePicker onDateChange={handleDateChange} />
		</div>

		{#if error}
			<div class="card bg-danger-500/10" style="border-color: rgb(244 63 94 / 0.5);">
				<p class="text-danger-400">{error}</p>
			</div>
		{:else}
			<!-- Persona Next Actions -->
			<div class="card stagger-enter" style="animation-delay: 160ms;">
				<div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
					<div>
						<h2 class="text-sm font-semibold text-ink-200">Next actions</h2>
						<p class="text-xs text-ink-400 mt-1">{personaContent.nextActionsCopy}</p>
					</div>

					<div class="flex flex-wrap items-center gap-2">
						{#each personaContent.actions as action (action.href)}
							<a
								href={`${base}${action.href}`}
								class={`btn ${action.variant === 'primary' ? 'btn-primary' : 'btn-secondary'} text-sm`}
								>{action.label}</a
							>
						{/each}
					</div>
				</div>
			</div>

			<!-- Stats Grid -->
			<StatsGrid
				{costs}
				{carbon}
				{zombieCount}
				totalMonthlyWaste={zombies?.total_monthly_waste}
				{periodLabel}
			/>

			{#if persona === 'engineering'}
				{#if engineeringDashboardSection}
					{@const EngineeringDashboardSection = engineeringDashboardSection}
					<EngineeringDashboardSection
						{zombies}
						{analysisText}
						{zombieCount}
						onRemediate={handleRemediate}
					/>
				{:else if engineeringDashboardSectionError}
					<div class="card bg-danger-500/10" style="border-color: rgb(244 63 94 / 0.5);">
						<p class="text-danger-400">{engineeringDashboardSectionError}</p>
					</div>
				{:else}
					<div
						class="glass-panel flex min-h-48 items-center justify-center text-ink-400"
						aria-busy="true"
					>
						<p>Loading engineering insights...</p>
					</div>
				{/if}
			{/if}

			<!-- Data Freshness Status -->
			{#if freshness}
				<div class="freshness-indicator stagger-enter" style="animation-delay: 240ms;">
					<div class="flex items-center gap-2">
						<Clock class="h-4 w-4 text-ink-400" />
						<span class="text-sm text-ink-400">Data Freshness:</span>
						{#if freshness.status === 'final'}
							<span class="badge badge-success">✓ Finalized</span>
						{:else if freshness.status === 'preliminary'}
							<span class="badge badge-warning flex items-center gap-1">
								<AlertTriangle class="h-3 w-3" />
								Preliminary ({freshness.preliminary_records} records may change)
							</span>
						{:else if freshness.status === 'mixed'}
							<span class="badge badge-default">
								{freshness.freshness_percentage}% Finalized
							</span>
						{:else}
							<span class="badge badge-default">No Data</span>
						{/if}
					</div>
					{#if freshness.latest_record_date}
						<span class="text-xs text-ink-500">Latest: {freshness.latest_record_date}</span>
					{/if}
				</div>
			{/if}

			{#if persona === 'finance' || persona === 'leadership'}
				{#if financeDashboardSection}
					{@const FinanceDashboardSection = financeDashboardSection}
					<FinanceDashboardSection {allocation} {tier} {unitEconomics} />
				{:else if financeDashboardSectionError}
					<div class="card bg-danger-500/10" style="border-color: rgb(244 63 94 / 0.5);">
						<p class="text-danger-400">{financeDashboardSectionError}</p>
					</div>
				{:else}
					<div
						class="glass-panel flex min-h-48 items-center justify-center text-ink-400"
						aria-busy="true"
					>
						<p>Loading finance insights...</p>
					</div>
				{/if}
			{/if}
		{/if}
	</div>
</AuthGate>

{#if remediationModalOpen && remediationCandidate}
	{#if remediationModalComponent}
		{@const RemediationModal = remediationModalComponent}
		<RemediationModal
			bind:isOpen={remediationModalOpen}
			finding={remediationCandidate}
			accessToken={data.session?.access_token}
			onClose={() => {
				remediationCandidate = null;
			}}
		/>
	{:else if remediationModalError}
		<div class="fixed inset-0 z-[120] flex items-center justify-center bg-ink-950/70 px-4">
			<div class="card max-w-md text-center">
				<p class="text-danger-400">{remediationModalError}</p>
			</div>
		</div>
	{:else}
		<div class="fixed inset-0 z-[120] flex items-center justify-center bg-ink-950/70 px-4">
			<div class="card max-w-md text-center" aria-busy="true">
				<p class="text-ink-300">Loading remediation workflow...</p>
			</div>
		</div>
	{/if}
{/if}
