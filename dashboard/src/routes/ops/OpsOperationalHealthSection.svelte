<script lang="ts">
	import { onMount } from 'svelte';
	import UpgradeNotice from '$lib/components/UpgradeNotice.svelte';
	import {
		canAccessOpsAcceptanceEvidence,
		canAccessOpsCloseWorkflow,
		canAccessOpsJobSlo
	} from '$lib/entitlements';
	import OpsStatusBanners from './OpsStatusBanners.svelte';
	import {
		loadOpsAcceptanceKpiSection,
		loadOpsCloseWorkflowSection,
		loadOpsIngestionSlaSection,
		loadOpsIntegrationAcceptanceSection,
		loadOpsJobSloSection,
		loadOpsUnitEconomicsSection,
		type OpsAcceptanceActions,
		type OpsCloseActions,
		type OpsReliabilityActions
	} from './opsOperationalSectionLoaders';
	import { buildOpsOperationalInitialState } from './opsOperationalState';
	import { createOpsOperationalUnitActions } from './opsOperationalUnitActions';
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
	let { data } = $props();
	const opsState = $state(buildOpsOperationalInitialState());
	let reliabilityAnchor: HTMLDivElement | null = $state(null);
	let advancedEvidenceAnchor: HTMLDivElement | null = $state(null);
	let reliabilityVisible = $state(false);
	let advancedEvidenceVisible = $state(false);
	let reliabilityLoaded = $state(false);
	let acceptanceActions = $state<OpsAcceptanceActions | null>(null);
	let closeActions = $state<OpsCloseActions | null>(null);
	let reliabilityActions = $state<OpsReliabilityActions | null>(null);
	let advancedActionsPromise: Promise<void> | null = null;
	let reliabilityActionsPromise: Promise<OpsReliabilityActions> | null = null;
	let opsAcceptanceActionsModulePromise: Promise<
		typeof import('./opsOperationalAcceptanceActions')
	> | null = null;
	let opsCloseActionsModulePromise: Promise<typeof import('./opsOperationalCloseActions')> | null =
		null;
	let opsReliabilityActionsModulePromise: Promise<
		typeof import('./opsOperationalReliabilityActions')
	> | null = null;
	const canAccessJobSlo = () => canAccessOpsJobSlo(data.subscription?.tier, data.profile?.role);
	const canAccessAcceptanceKpis = () =>
		canAccessOpsAcceptanceEvidence(data.subscription?.tier, data.profile?.role);
	const canAccessCloseWorkflow = () =>
		canAccessOpsCloseWorkflow(data.subscription?.tier, data.profile?.role);

	const unitActions = createOpsOperationalUnitActions({
		getData: () => data,
		state: opsState,
		requestTimeoutMs: OPS_REQUEST_TIMEOUT_MS
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

	function loadOpsAcceptanceActionsModule() {
		if (!opsAcceptanceActionsModulePromise) {
			opsAcceptanceActionsModulePromise = import('./opsOperationalAcceptanceActions');
		}

		return opsAcceptanceActionsModulePromise;
	}

	function loadOpsCloseActionsModule() {
		if (!opsCloseActionsModulePromise) {
			opsCloseActionsModulePromise = import('./opsOperationalCloseActions');
		}

		return opsCloseActionsModulePromise;
	}

	function loadOpsReliabilityActionsModule() {
		if (!opsReliabilityActionsModulePromise) {
			opsReliabilityActionsModulePromise = import('./opsOperationalReliabilityActions');
		}

		return opsReliabilityActionsModulePromise;
	}

	async function ensureAdvancedActionModules(): Promise<void> {
		if (acceptanceActions && (!canAccessCloseWorkflow() || closeActions)) {
			return;
		}

		if (!advancedActionsPromise) {
			advancedActionsPromise = (async () => {
				const acceptanceModule = await loadOpsAcceptanceActionsModule();
				acceptanceActions ??= acceptanceModule.createOpsOperationalAcceptanceActions({
					getData: () => data,
					state: opsState
				});

				if (canAccessCloseWorkflow()) {
					const closeModule = await loadOpsCloseActionsModule();
					closeActions ??= closeModule.createOpsOperationalCloseActions({
						getData: () => data,
						state: opsState
					});
				}
			})().catch((error) => {
				advancedActionsPromise = null;
				throw error;
			});
		}

		await advancedActionsPromise;
	}

	async function ensureReliabilityActions(): Promise<OpsReliabilityActions> {
		if (reliabilityActions) {
			return reliabilityActions;
		}

		if (!reliabilityActionsPromise) {
			reliabilityActionsPromise = loadOpsReliabilityActionsModule()
				.then((module) =>
					module.createOpsOperationalReliabilityActions({
						getData: () => data,
						state: opsState,
						requestTimeoutMs: OPS_REQUEST_TIMEOUT_MS,
						access: {
							jobSlo: canAccessJobSlo
						}
					})
				)
				.then((actions) => {
					reliabilityActions = actions;
					return actions;
				})
				.catch((error) => {
					reliabilityActionsPromise = null;
					throw error;
				});
		}

		return reliabilityActionsPromise;
	}

	async function refreshIngestionSla() {
		const actions = await ensureReliabilityActions();
		await actions.refreshIngestionSla();
	}

	async function refreshJobSlo() {
		const actions = await ensureReliabilityActions();
		await actions.refreshJobSlo();
	}

	$effect(() => {
		if (!reliabilityVisible || reliabilityLoaded) return;
		reliabilityLoaded = true;
		void ensureReliabilityActions().then((actions) =>
			actions.loadReliabilityData({ silent: true })
		);
	});

	$effect(() => {
		if (!advancedEvidenceVisible) return;
		void ensureAdvancedActionModules()
			.then(() => {
				void acceptanceActions?.preloadAcceptanceEvidence({
					includeKpis: canAccessAcceptanceKpis(),
					includeRuns: true
				});
				if (canAccessCloseWorkflow()) {
					void closeActions?.preloadClosePackage();
				}
			})
			.catch(() => {
				advancedActionsPromise = null;
			});
	});

	onMount(() => {
		if (import.meta.env.MODE === 'test' || typeof IntersectionObserver === 'undefined') {
			reliabilityVisible = true;
			advancedEvidenceVisible = true;
			void unitActions.loadPrimaryOperationalData();
			return;
		}

		const reliabilityObserver = new IntersectionObserver(
			(entries) => {
				if (entries.some((entry) => entry.isIntersecting)) {
					reliabilityVisible = true;
					reliabilityObserver.disconnect();
				}
			},
			{ rootMargin: '200px 0px' }
		);

		const advancedObserver = new IntersectionObserver(
			(entries) => {
				if (entries.some((entry) => entry.isIntersecting)) {
					advancedEvidenceVisible = true;
					advancedObserver.disconnect();
				}
			},
			{ rootMargin: '240px 0px' }
		);

		if (reliabilityAnchor) {
			reliabilityObserver.observe(reliabilityAnchor);
		}

		if (advancedEvidenceAnchor) {
			advancedObserver.observe(advancedEvidenceAnchor);
		}

		void unitActions.loadPrimaryOperationalData();
		return () => {
			reliabilityObserver.disconnect();
			advancedObserver.disconnect();
		};
	});
</script>

<div class="space-y-6">
	<OpsStatusBanners error={opsState.error} success={opsState.success} />
	{#await loadOpsUnitEconomicsSection()}
		<div class="card">
			<div class="skeleton h-8 w-48 mb-4"></div>
			<div class="skeleton h-4 w-full mb-2"></div>
			<div class="skeleton h-40 rounded-2xl"></div>
		</div>
	{:then module}
		{@const OpsUnitEconomicsSection = module.default}
		<OpsUnitEconomicsSection
			{...{
				refreshingUnitEconomics: opsState.refreshingUnitEconomics,
				refreshUnitEconomics: unitActions.refreshUnitEconomics,
				unitEconomics: opsState.unitEconomics,
				saveUnitEconomicsSettings: unitActions.saveUnitEconomicsSettings,
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
	{/await}

	<div bind:this={reliabilityAnchor}>
		{#if reliabilityVisible}
			{#await loadOpsIngestionSlaSection()}
				<div class="card">
					<div class="skeleton h-8 w-48 mb-4"></div>
					<div class="skeleton h-40 rounded-2xl"></div>
				</div>
			{:then module}
				{@const OpsIngestionSlaSection = module.default}
				<OpsIngestionSlaSection
					{...{
						refreshingIngestionSla: opsState.refreshingIngestionSla,
						refreshIngestionSla,
						ingestionSla: opsState.ingestionSla,
						ingestionSlaBadgeClass,
						formatNumber: formatNumberSafe,
						formatDuration: formatDurationSafe,
						formatDate: formatDateSafe
					}}
					bind:ingestionSlaWindowHours={opsState.ingestionSlaWindowHours}
				/>
			{:catch}
				<div class="card">
					<div class="skeleton h-8 w-48 mb-4"></div>
				</div>
			{/await}

			{#if canAccessJobSlo()}
				{#await loadOpsJobSloSection()}
					<div class="card">
						<div class="skeleton h-8 w-48 mb-4"></div>
						<div class="skeleton h-40 rounded-2xl"></div>
					</div>
				{:then module}
					{@const OpsJobSloSection = module.default}
					<OpsJobSloSection
						{...{
							refreshingJobSlo: opsState.refreshingJobSlo,
							refreshJobSlo,
							jobSlo: opsState.jobSlo,
							jobSloBadgeClass,
							jobSloMetricBadgeClass,
							formatDuration: formatDurationSafe
						}}
						bind:jobSloWindowHours={opsState.jobSloWindowHours}
					/>
				{:catch}
					<div class="card">
						<div class="skeleton h-8 w-48 mb-4"></div>
					</div>
				{/await}
			{:else}
				<UpgradeNotice
					currentTier={data.subscription?.tier}
					requiredTier="pro"
					feature="job reliability SLO evidence"
				/>
			{/if}
		{:else}
			<div class="card">
				<div class="skeleton h-8 w-48 mb-4"></div>
				<div class="skeleton h-40 rounded-2xl"></div>
			</div>
		{/if}
	</div>

	<div bind:this={advancedEvidenceAnchor}>
		{#if advancedEvidenceVisible}
			{#if acceptanceActions}
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
					{#if closeActions}
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
						<div class="card">
							<div class="skeleton h-8 w-64 mb-4"></div>
							<div class="skeleton h-56 rounded-2xl"></div>
						</div>
					{/if}
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
				<div class="card">
					<div class="skeleton h-8 w-64 mb-4"></div>
					<div class="skeleton h-56 rounded-2xl"></div>
				</div>
				{#if canAccessCloseWorkflow()}
					<div class="card">
						<div class="skeleton h-8 w-64 mb-4"></div>
						<div class="skeleton h-56 rounded-2xl"></div>
					</div>
				{/if}
			{/if}
		{:else}
			<div class="card">
				<div class="skeleton h-8 w-56 mb-4"></div>
				<div class="skeleton h-56 rounded-2xl"></div>
			</div>
			<div class="card">
				<div class="skeleton h-8 w-64 mb-4"></div>
				<div class="skeleton h-56 rounded-2xl"></div>
			</div>
			{#if canAccessCloseWorkflow()}
				<div class="card">
					<div class="skeleton h-8 w-64 mb-4"></div>
					<div class="skeleton h-56 rounded-2xl"></div>
				</div>
			{/if}
		{/if}
	</div>
</div>
