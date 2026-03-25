<script lang="ts">
	import { onMount } from 'svelte';
	import UpgradeNotice from '$lib/components/UpgradeNotice.svelte';
	import { createLazyComponent } from '$lib/lazyComponent';
	import {
		canAccessOpsAcceptanceEvidence,
		canAccessOpsCloseWorkflow,
		canAccessOpsJobSlo
	} from '$lib/entitlements';
	import OpsStatusBanners from './OpsStatusBanners.svelte';
	import OpsIngestionSlaSection from './OpsIngestionSlaSection.svelte';
	import OpsJobSloSection from './OpsJobSloSection.svelte';
	import OpsUnitEconomicsSection from './OpsUnitEconomicsSection.svelte';
	import { buildOpsOperationalInitialState } from './opsOperationalState';
	import { createOpsOperationalCoreActions } from './opsOperationalCoreActions';
	import { createOpsOperationalAcceptanceActions } from './opsOperationalAcceptanceActions';
	import { createOpsOperationalCloseActions } from './opsOperationalCloseActions';
	import {
		acceptanceBadgeClass,
		closeStatusBadgeClass,
		formatDate,
		formatDuration,
		formatNumber,
		formatUsd,
		ingestionSlaBadgeClass,
		jobSloBadgeClass,
		jobSloMetricBadgeClass
	} from './opsUtils';
	import { formatDelta, unitDeltaClass } from './unitEconomics';

	const OPS_REQUEST_TIMEOUT_MS = 10000;
	const loadOpsAcceptanceKpiSection = createLazyComponent(
		() => import('./OpsAcceptanceKpiSection.svelte')
	);
	const loadOpsIntegrationAcceptanceSection = createLazyComponent(
		() => import('./OpsIntegrationAcceptanceSection.svelte')
	);
	const loadOpsCloseWorkflowSection = createLazyComponent(
		() => import('./OpsCloseWorkflowSection.svelte')
	);

	let { data } = $props();
	const opsState = $state(buildOpsOperationalInitialState());
	let advancedEvidenceAnchor: HTMLDivElement | null = $state(null);
	let advancedEvidenceVisible = $state(false);
	const canAccessJobSlo = () => canAccessOpsJobSlo(data.subscription?.tier, data.profile?.role);
	const canAccessAcceptanceKpis = () =>
		canAccessOpsAcceptanceEvidence(data.subscription?.tier, data.profile?.role);
	const canAccessCloseWorkflow = () =>
		canAccessOpsCloseWorkflow(data.subscription?.tier, data.profile?.role);

	const coreActions = createOpsOperationalCoreActions({
		getData: () => data,
		state: opsState,
		requestTimeoutMs: OPS_REQUEST_TIMEOUT_MS,
		access: {
			jobSlo: canAccessJobSlo,
			acceptanceKpis: canAccessAcceptanceKpis,
			closeWorkflow: canAccessCloseWorkflow
		}
	});

	const acceptanceActions = createOpsOperationalAcceptanceActions({
		getData: () => data,
		state: opsState
	});

	const closeActions = createOpsOperationalCloseActions({
		getData: () => data,
		state: opsState
	});

	const formatUsdSafe = (value: number | null | undefined): string => formatUsd(Number(value ?? 0));
	const formatNumberSafe = (value: number | null | undefined, digits?: number): string =>
		formatNumber(Number(value ?? 0), digits);
	const formatDurationSafe = (value: number | null | undefined): string =>
		formatDuration(value ?? null);
	const formatDateSafe = (value: string | null | undefined): string => formatDate(value ?? null);
	const formatDeltaSafe = (value: number | null | undefined): string =>
		formatDelta(Number(value ?? 0));
	const closeStatusBadgeClassSafe = (value: string | null | undefined): string =>
		closeStatusBadgeClass(value ?? undefined);

	onMount(() => {
		if (import.meta.env.MODE === 'test' || typeof IntersectionObserver === 'undefined') {
			advancedEvidenceVisible = true;
		} else {
			const observer = new IntersectionObserver(
				(entries) => {
					if (entries.some((entry) => entry.isIntersecting)) {
						advancedEvidenceVisible = true;
						observer.disconnect();
					}
				},
				{ rootMargin: '240px 0px' }
			);

			if (advancedEvidenceAnchor) {
				observer.observe(advancedEvidenceAnchor);
			}

			void coreActions.loadOperationalData();
			return () => observer.disconnect();
		}

		void coreActions.loadOperationalData();
	});
</script>

<div class="space-y-6">
	<OpsStatusBanners error={opsState.error} success={opsState.success} />
	<OpsUnitEconomicsSection
		{...{
			refreshingUnitEconomics: opsState.refreshingUnitEconomics,
			refreshUnitEconomics: coreActions.refreshUnitEconomics,
			unitEconomics: opsState.unitEconomics,
			saveUnitEconomicsSettings: coreActions.saveUnitEconomicsSettings,
			savingUnitSettings: opsState.savingUnitSettings,
			formatUsd: formatUsdSafe,
			formatNumber: formatNumberSafe,
			formatDelta: formatDeltaSafe,
			unitDeltaClass
		}}
		bind:unitStartDate={opsState.unitStartDate}
		bind:unitEndDate={opsState.unitEndDate}
		bind:unitAlertOnAnomaly={opsState.unitAlertOnAnomaly}
		bind:unitSettings={opsState.unitSettings}
	/>

	<OpsIngestionSlaSection
		{...{
			refreshingIngestionSla: opsState.refreshingIngestionSla,
			refreshIngestionSla: coreActions.refreshIngestionSla,
			ingestionSla: opsState.ingestionSla,
			ingestionSlaBadgeClass,
			formatNumber: formatNumberSafe,
			formatDuration: formatDurationSafe,
			formatDate: formatDateSafe
		}}
		bind:ingestionSlaWindowHours={opsState.ingestionSlaWindowHours}
	/>

	{#if canAccessJobSlo()}
		<OpsJobSloSection
			{...{
				refreshingJobSlo: opsState.refreshingJobSlo,
				refreshJobSlo: coreActions.refreshJobSlo,
				jobSlo: opsState.jobSlo,
				jobSloBadgeClass,
				jobSloMetricBadgeClass,
				formatDuration: formatDurationSafe
			}}
			bind:jobSloWindowHours={opsState.jobSloWindowHours}
		/>
	{:else}
		<UpgradeNotice
			currentTier={data.subscription?.tier}
			requiredTier="pro"
			feature="job reliability SLO evidence"
		/>
	{/if}

	<div bind:this={advancedEvidenceAnchor}>
		{#if advancedEvidenceVisible}
			{#if canAccessAcceptanceKpis()}
				{#await loadOpsAcceptanceKpiSection()}
					<div class="card">
						<div class="skeleton h-8 w-56 mb-4"></div>
						<div class="skeleton h-56 rounded-2xl"></div>
					</div>
				{:then module}
					{@const OpsAcceptanceKpiSection = module.default}
					<OpsAcceptanceKpiSection
						{...{
							capturingAcceptanceKpis: opsState.capturingAcceptanceKpis,
							downloadingAcceptanceJson: opsState.downloadingAcceptanceJson,
							downloadingAcceptanceCsv: opsState.downloadingAcceptanceCsv,
							refreshingAcceptanceKpis: opsState.refreshingAcceptanceKpis,
							refreshingAcceptanceKpiHistory: opsState.refreshingAcceptanceKpiHistory,
							captureAcceptanceKpis: acceptanceActions.captureAcceptanceKpis,
							downloadAcceptanceKpiJson: acceptanceActions.downloadAcceptanceKpiJson,
							downloadAcceptanceKpiCsv: acceptanceActions.downloadAcceptanceKpiCsv,
							refreshAcceptanceKpis: acceptanceActions.refreshAcceptanceKpis,
							refreshAcceptanceKpiHistory: acceptanceActions.refreshAcceptanceKpiHistory,
							acceptanceKpis: opsState.acceptanceKpis,
							acceptanceKpiHistory: opsState.acceptanceKpiHistory,
							lastAcceptanceKpiCapture: opsState.lastAcceptanceKpiCapture,
							acceptanceBadgeClass,
							formatDate: formatDateSafe
						}}
					/>
				{:catch}
					<div class="card">
						<div class="skeleton h-8 w-56 mb-4"></div>
					</div>
				{/await}
			{:else}
				<UpgradeNotice
					currentTier={data.subscription?.tier}
					requiredTier="pro"
					feature="acceptance KPI evidence"
				/>
			{/if}

			{#await loadOpsIntegrationAcceptanceSection()}
				<div class="card">
					<div class="skeleton h-8 w-64 mb-4"></div>
					<div class="skeleton h-56 rounded-2xl"></div>
				</div>
			{:then module}
				{@const OpsIntegrationAcceptanceSection = module.default}
				<OpsIntegrationAcceptanceSection
					{...{
						runningAcceptanceSuite: opsState.runningAcceptanceSuite,
						capturingAcceptanceRuns: opsState.capturingAcceptanceRuns,
						capturingAcceptanceKpis: opsState.capturingAcceptanceKpis,
						refreshingAcceptanceRuns: opsState.refreshingAcceptanceRuns,
						refreshingAcceptanceKpiHistory: opsState.refreshingAcceptanceKpiHistory,
						runAcceptanceSuite: acceptanceActions.runAcceptanceSuite,
						captureAcceptanceRuns: acceptanceActions.captureAcceptanceRuns,
						refreshAcceptanceRuns: acceptanceActions.refreshAcceptanceRuns,
						lastAcceptanceCapture: opsState.lastAcceptanceCapture,
						acceptanceRuns: opsState.acceptanceRuns,
						hasSelectedAcceptanceChannels: acceptanceActions.hasSelectedAcceptanceChannels,
						acceptanceRunStatusClass: acceptanceActions.acceptanceRunStatusClass,
						formatDate: formatDateSafe
					}}
					bind:captureIncludeSlack={opsState.captureIncludeSlack}
					bind:captureIncludeJira={opsState.captureIncludeJira}
					bind:captureIncludeWorkflow={opsState.captureIncludeWorkflow}
					bind:captureFailFast={opsState.captureFailFast}
				/>
			{:catch}
				<div class="card">
					<div class="skeleton h-8 w-64 mb-4"></div>
				</div>
			{/await}

			{#if canAccessCloseWorkflow()}
				{#await loadOpsCloseWorkflowSection()}
					<div class="card">
						<div class="skeleton h-8 w-64 mb-4"></div>
						<div class="skeleton h-56 rounded-2xl"></div>
					</div>
				{:then module}
					{@const OpsCloseWorkflowSection = module.default}
					<OpsCloseWorkflowSection
						{...{
							refreshingClosePackage: opsState.refreshingClosePackage,
							previewClosePackage: closeActions.previewClosePackage,
							downloadingCloseJson: opsState.downloadingCloseJson,
							downloadClosePackageJson: closeActions.downloadClosePackageJson,
							downloadingCloseCsv: opsState.downloadingCloseCsv,
							downloadClosePackageCsv: closeActions.downloadClosePackageCsv,
							downloadingRestatementCsv: opsState.downloadingRestatementCsv,
							downloadRestatementCsv: closeActions.downloadRestatementCsv,
							closePackage: opsState.closePackage,
							saveProviderInvoice: closeActions.saveProviderInvoice,
							savingInvoice: opsState.savingInvoice,
							deletingInvoice: opsState.deletingInvoice,
							deleteProviderInvoice: closeActions.deleteProviderInvoice,
							closeStatusBadgeClass: closeStatusBadgeClassSafe,
							formatUsd: formatUsdSafe
						}}
						bind:closeStartDate={opsState.closeStartDate}
						bind:closeEndDate={opsState.closeEndDate}
						bind:closeProvider={opsState.closeProvider}
						bind:invoiceForm={opsState.invoiceForm}
					/>
				{:catch}
					<div class="card">
						<div class="skeleton h-8 w-64 mb-4"></div>
					</div>
				{/await}
			{:else}
				<UpgradeNotice
					currentTier={data.subscription?.tier}
					requiredTier="pro"
					feature="reconciliation close workflow"
				/>
			{/if}
		{:else}
			<div class="card">
				<div class="skeleton h-8 w-56 mb-4"></div>
				<div class="skeleton h-56 rounded-2xl"></div>
			</div>
		{/if}
	</div>
</div>
