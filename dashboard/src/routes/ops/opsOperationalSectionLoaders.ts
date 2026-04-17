import { createLazyComponent } from '$lib/lazyComponent';
import type {
	IngestionSLAResponse,
	JobSLOResponse,
	UnitEconomicsResponse,
	UnitEconomicsSettings
} from './opsTypes';

export const loadOpsAcceptanceKpiSection = createLazyComponent(
	() => import('./OpsAcceptanceKpiSection.svelte')
);

export const loadOpsUnitEconomicsSection = createLazyComponent<{
	unitStartDate: string;
	unitEndDate: string;
	unitAlertOnAnomaly: boolean;
	refreshingUnitEconomics: boolean;
	refreshUnitEconomics: () => void | Promise<void>;
	unitEconomics: UnitEconomicsResponse | null;
	unitSettings: UnitEconomicsSettings | null;
	saveUnitEconomicsSettings: (event?: SubmitEvent) => void | Promise<void>;
	savingUnitSettings: boolean;
	formatUsd: (value: number | null | undefined) => string;
	formatNumber: (value: number | null | undefined, digits?: number) => string;
	formatDelta: (value: number | null | undefined) => string;
	unitDeltaClass: (metric: UnitEconomicsResponse['metrics'][number]) => string;
}>(() => import('./OpsUnitEconomicsSection.svelte'));

export const loadOpsIntegrationAcceptanceSection = createLazyComponent(
	() => import('./OpsIntegrationAcceptanceSection.svelte')
);

export const loadOpsCloseWorkflowSection = createLazyComponent(
	() => import('./OpsCloseWorkflowSection.svelte')
);

export const loadOpsIngestionSlaSection = createLazyComponent<{
	ingestionSlaWindowHours: number;
	refreshingIngestionSla: boolean;
	refreshIngestionSla: () => void | Promise<void>;
	ingestionSla: IngestionSLAResponse | null;
	ingestionSlaBadgeClass: (value: IngestionSLAResponse) => string;
	formatNumber: (value: number | null | undefined, digits?: number) => string;
	formatDuration: (value: number | null | undefined) => string;
	formatDate: (value: string | null | undefined) => string;
}>(() => import('./OpsIngestionSlaSection.svelte'));

export const loadOpsJobSloSection = createLazyComponent<{
	jobSloWindowHours: number;
	refreshingJobSlo: boolean;
	refreshJobSlo: () => void | Promise<void>;
	jobSlo: JobSLOResponse | null;
	jobSloBadgeClass: (value: JobSLOResponse) => string;
	jobSloMetricBadgeClass: (metric: JobSLOResponse['metrics'][number]) => string;
	formatDuration: (value: number | null | undefined) => string;
}>(() => import('./OpsJobSloSection.svelte'));

export type OpsAcceptanceActions = {
	refreshAcceptanceKpis: () => Promise<void>;
	refreshAcceptanceKpiHistory: () => Promise<void>;
	preloadAcceptanceEvidence: (options?: {
		includeKpis?: boolean;
		includeRuns?: boolean;
	}) => Promise<void>;
	captureAcceptanceKpis: () => Promise<void>;
	refreshAcceptanceRuns: () => Promise<void>;
	captureAcceptanceRuns: () => Promise<void>;
	runAcceptanceSuite: () => Promise<void>;
	downloadAcceptanceKpiJson: () => Promise<void>;
	downloadAcceptanceKpiCsv: () => Promise<void>;
	hasSelectedAcceptanceChannels: (
		includeSlack: boolean,
		includeJira: boolean,
		includeWorkflow: boolean
	) => boolean;
	acceptanceRunStatusClass: (status: string) => string;
};

export type OpsCloseActions = {
	previewClosePackage: () => Promise<void>;
	preloadClosePackage: () => Promise<void>;
	saveProviderInvoice: (event?: SubmitEvent) => Promise<void>;
	deleteProviderInvoice: () => Promise<void>;
	downloadClosePackageJson: () => Promise<void>;
	downloadClosePackageCsv: () => Promise<void>;
	downloadRestatementCsv: () => Promise<void>;
};

export type OpsReliabilityActions = {
	loadReliabilityData: (options?: { silent?: boolean }) => Promise<void>;
	refreshIngestionSla: () => Promise<void>;
	refreshJobSlo: () => Promise<void>;
};
