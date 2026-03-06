<script lang="ts">
	import { onMount } from 'svelte';
	import OpsStatusBanners from './OpsStatusBanners.svelte';
	import OpsAcceptanceKpiSection from './OpsAcceptanceKpiSection.svelte';
	import OpsCloseWorkflowSection from './OpsCloseWorkflowSection.svelte';
	import OpsIngestionSlaSection from './OpsIngestionSlaSection.svelte';
	import OpsIntegrationAcceptanceSection from './OpsIntegrationAcceptanceSection.svelte';
	import OpsJobSloSection from './OpsJobSloSection.svelte';
	import OpsUnitEconomicsSection from './OpsUnitEconomicsSection.svelte';
	import {
		buildOpsOperationalInitialState
	} from './opsOperationalState';
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
	import {
		formatDelta,
		unitDeltaClass
	} from './unitEconomics';

	const OPS_REQUEST_TIMEOUT_MS = 10000;

	let { data } = $props();
	const state = $state(buildOpsOperationalInitialState());

	const coreActions = createOpsOperationalCoreActions({
		getData: () => data,
		state,
		requestTimeoutMs: OPS_REQUEST_TIMEOUT_MS
	});

	const acceptanceActions = createOpsOperationalAcceptanceActions({
		getData: () => data,
		state
	});

	const closeActions = createOpsOperationalCloseActions({
		getData: () => data,
		state
	});

	const formatUsdSafe = (value: number | null | undefined): string => formatUsd(Number(value ?? 0));
	const formatNumberSafe = (value: number | null | undefined, digits?: number): string =>
		formatNumber(Number(value ?? 0), digits);
	const formatDurationSafe = (value: number | null | undefined): string => formatDuration(value ?? null);
	const formatDateSafe = (value: string | null | undefined): string => formatDate(value ?? null);
	const formatDeltaSafe = (value: number | null | undefined): string => formatDelta(Number(value ?? 0));
	const closeStatusBadgeClassSafe = (value: string | null | undefined): string =>
		closeStatusBadgeClass(value ?? undefined);

	onMount(() => {
		void coreActions.loadOperationalData();
	});
</script>

<div class="space-y-6">
	<OpsStatusBanners error={state.error} success={state.success} />
	<OpsUnitEconomicsSection
		{...{
			refreshingUnitEconomics: state.refreshingUnitEconomics,
			refreshUnitEconomics: coreActions.refreshUnitEconomics,
			unitEconomics: state.unitEconomics,
			saveUnitEconomicsSettings: coreActions.saveUnitEconomicsSettings,
			savingUnitSettings: state.savingUnitSettings,
			formatUsd: formatUsdSafe,
			formatNumber: formatNumberSafe,
			formatDelta: formatDeltaSafe,
			unitDeltaClass
		}}
		bind:unitStartDate={state.unitStartDate}
		bind:unitEndDate={state.unitEndDate}
		bind:unitAlertOnAnomaly={state.unitAlertOnAnomaly}
		bind:unitSettings={state.unitSettings}
	/>

	<OpsIngestionSlaSection
		{...{
			refreshingIngestionSla: state.refreshingIngestionSla,
			refreshIngestionSla: coreActions.refreshIngestionSla,
			ingestionSla: state.ingestionSla,
			ingestionSlaBadgeClass,
			formatNumber: formatNumberSafe,
			formatDuration: formatDurationSafe,
			formatDate: formatDateSafe
		}}
		bind:ingestionSlaWindowHours={state.ingestionSlaWindowHours}
	/>

	<OpsJobSloSection
		{...{
			refreshingJobSlo: state.refreshingJobSlo,
			refreshJobSlo: coreActions.refreshJobSlo,
			jobSlo: state.jobSlo,
			jobSloBadgeClass,
			jobSloMetricBadgeClass,
			formatDuration: formatDurationSafe
		}}
		bind:jobSloWindowHours={state.jobSloWindowHours}
	/>

	<OpsAcceptanceKpiSection
		{...{
			capturingAcceptanceKpis: state.capturingAcceptanceKpis,
			downloadingAcceptanceJson: state.downloadingAcceptanceJson,
			downloadingAcceptanceCsv: state.downloadingAcceptanceCsv,
			refreshingAcceptanceKpis: state.refreshingAcceptanceKpis,
			refreshingAcceptanceKpiHistory: state.refreshingAcceptanceKpiHistory,
			captureAcceptanceKpis: acceptanceActions.captureAcceptanceKpis,
			downloadAcceptanceKpiJson: acceptanceActions.downloadAcceptanceKpiJson,
			downloadAcceptanceKpiCsv: acceptanceActions.downloadAcceptanceKpiCsv,
			refreshAcceptanceKpis: acceptanceActions.refreshAcceptanceKpis,
			refreshAcceptanceKpiHistory: acceptanceActions.refreshAcceptanceKpiHistory,
			acceptanceKpis: state.acceptanceKpis,
			acceptanceKpiHistory: state.acceptanceKpiHistory,
			lastAcceptanceKpiCapture: state.lastAcceptanceKpiCapture,
			acceptanceBadgeClass,
			formatDate: formatDateSafe
		}}
	/>

	<OpsIntegrationAcceptanceSection
		{...{
			runningAcceptanceSuite: state.runningAcceptanceSuite,
			capturingAcceptanceRuns: state.capturingAcceptanceRuns,
			capturingAcceptanceKpis: state.capturingAcceptanceKpis,
			refreshingAcceptanceRuns: state.refreshingAcceptanceRuns,
			refreshingAcceptanceKpiHistory: state.refreshingAcceptanceKpiHistory,
			runAcceptanceSuite: acceptanceActions.runAcceptanceSuite,
			captureAcceptanceRuns: acceptanceActions.captureAcceptanceRuns,
			refreshAcceptanceRuns: acceptanceActions.refreshAcceptanceRuns,
			lastAcceptanceCapture: state.lastAcceptanceCapture,
			acceptanceRuns: state.acceptanceRuns,
			hasSelectedAcceptanceChannels: acceptanceActions.hasSelectedAcceptanceChannels,
			acceptanceRunStatusClass: acceptanceActions.acceptanceRunStatusClass,
			formatDate: formatDateSafe
		}}
		bind:captureIncludeSlack={state.captureIncludeSlack}
		bind:captureIncludeJira={state.captureIncludeJira}
		bind:captureIncludeWorkflow={state.captureIncludeWorkflow}
		bind:captureFailFast={state.captureFailFast}
	/>

	<OpsCloseWorkflowSection
		{...{
			refreshingClosePackage: state.refreshingClosePackage,
			previewClosePackage: closeActions.previewClosePackage,
			downloadingCloseJson: state.downloadingCloseJson,
			downloadClosePackageJson: closeActions.downloadClosePackageJson,
			downloadingCloseCsv: state.downloadingCloseCsv,
			downloadClosePackageCsv: closeActions.downloadClosePackageCsv,
			downloadingRestatementCsv: state.downloadingRestatementCsv,
			downloadRestatementCsv: closeActions.downloadRestatementCsv,
			closePackage: state.closePackage,
			saveProviderInvoice: closeActions.saveProviderInvoice,
			savingInvoice: state.savingInvoice,
			deletingInvoice: state.deletingInvoice,
			deleteProviderInvoice: closeActions.deleteProviderInvoice,
			closeStatusBadgeClass: closeStatusBadgeClassSafe,
			formatUsd: formatUsdSafe
		}}
		bind:closeStartDate={state.closeStartDate}
		bind:closeEndDate={state.closeEndDate}
		bind:closeProvider={state.closeProvider}
		bind:invoiceForm={state.invoiceForm}
	/>
</div>
