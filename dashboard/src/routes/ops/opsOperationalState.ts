import { defaultDateWindow } from './unitEconomics';
import type {
	AcceptanceKpiCaptureResponse,
	AcceptanceKpiEvidenceItem,
	AcceptanceKpisResponse,
	IngestionSLAResponse,
	IntegrationAcceptanceCaptureResponse,
	IntegrationAcceptanceRun,
	JobSLOResponse,
	ProviderInvoiceForm,
	ReconciliationClosePackage,
	UnitEconomicsResponse,
	UnitEconomicsSettings
} from './opsTypes';

export interface OpsOperationalState {
	error: string;
	success: string;
	refreshingUnitEconomics: boolean;
	refreshingIngestionSla: boolean;
	refreshingJobSlo: boolean;
	refreshingAcceptanceKpis: boolean;
	refreshingAcceptanceKpiHistory: boolean;
	refreshingAcceptanceRuns: boolean;
	capturingAcceptanceRuns: boolean;
	capturingAcceptanceKpis: boolean;
	runningAcceptanceSuite: boolean;
	captureIncludeSlack: boolean;
	captureIncludeJira: boolean;
	captureIncludeWorkflow: boolean;
	captureFailFast: boolean;
	lastAcceptanceCapture: IntegrationAcceptanceCaptureResponse | null;
	refreshingClosePackage: boolean;
	savingInvoice: boolean;
	deletingInvoice: boolean;
	savingUnitSettings: boolean;
	downloadingAcceptanceJson: boolean;
	downloadingAcceptanceCsv: boolean;
	downloadingCloseJson: boolean;
	downloadingCloseCsv: boolean;
	downloadingRestatementCsv: boolean;
	unitStartDate: string;
	unitEndDate: string;
	unitAlertOnAnomaly: boolean;
	unitEconomics: UnitEconomicsResponse | null;
	unitSettings: UnitEconomicsSettings | null;
	ingestionSlaWindowHours: number;
	ingestionSla: IngestionSLAResponse | null;
	jobSloWindowHours: number;
	jobSlo: JobSLOResponse | null;
	acceptanceKpis: AcceptanceKpisResponse | null;
	acceptanceKpiHistory: AcceptanceKpiEvidenceItem[];
	lastAcceptanceKpiCapture: AcceptanceKpiCaptureResponse | null;
	acceptanceRuns: IntegrationAcceptanceRun[];
	closeStartDate: string;
	closeEndDate: string;
	closeProvider: string;
	closePackage: ReconciliationClosePackage | null;
	invoiceForm: ProviderInvoiceForm;
}

export interface OpsRuntimeData {
	user?: unknown;
	session?: {
		access_token?: string | null;
	} | null;
}

function buildInitialInvoiceForm(): ProviderInvoiceForm {
	return {
		invoice_number: '',
		currency: 'USD',
		total_amount: 0,
		status: 'submitted',
		notes: ''
	};
}

export function buildOpsOperationalInitialState(): OpsOperationalState {
	const unitWindow = defaultDateWindow(30);
	const closeWindow = defaultDateWindow(30);
	return {
		error: '',
		success: '',
		refreshingUnitEconomics: false,
		refreshingIngestionSla: false,
		refreshingJobSlo: false,
		refreshingAcceptanceKpis: false,
		refreshingAcceptanceKpiHistory: false,
		refreshingAcceptanceRuns: false,
		capturingAcceptanceRuns: false,
		capturingAcceptanceKpis: false,
		runningAcceptanceSuite: false,
		captureIncludeSlack: true,
		captureIncludeJira: true,
		captureIncludeWorkflow: true,
		captureFailFast: false,
		lastAcceptanceCapture: null,
		refreshingClosePackage: false,
		savingInvoice: false,
		deletingInvoice: false,
		savingUnitSettings: false,
		downloadingAcceptanceJson: false,
		downloadingAcceptanceCsv: false,
		downloadingCloseJson: false,
		downloadingCloseCsv: false,
		downloadingRestatementCsv: false,
		unitStartDate: unitWindow.start,
		unitEndDate: unitWindow.end,
		unitAlertOnAnomaly: true,
		unitEconomics: null,
		unitSettings: null,
		ingestionSlaWindowHours: 24,
		ingestionSla: null,
		jobSloWindowHours: 24 * 7,
		jobSlo: null,
		acceptanceKpis: null,
		acceptanceKpiHistory: [],
		lastAcceptanceKpiCapture: null,
		acceptanceRuns: [],
		closeStartDate: closeWindow.start,
		closeEndDate: closeWindow.end,
		closeProvider: 'all',
		closePackage: null,
		invoiceForm: buildInitialInvoiceForm()
	};
}

export function syncInvoiceFormFromClosePackage(state: OpsOperationalState): void {
	const pkg = state.closePackage;
	if (!pkg?.invoice_reconciliation) {
		return;
	}
	const invoice = pkg.invoice_reconciliation.invoice;
	if (invoice) {
		state.invoiceForm.invoice_number = invoice.invoice_number ? String(invoice.invoice_number) : '';
		state.invoiceForm.currency = normalizeCurrencyCode(invoice.currency);
		state.invoiceForm.total_amount = Number(invoice.total_amount ?? 0);
		state.invoiceForm.status = invoice.status ? String(invoice.status) : 'submitted';
		state.invoiceForm.notes = invoice.notes ? String(invoice.notes) : '';
		return;
	}
	state.invoiceForm.invoice_number = '';
	state.invoiceForm.currency = 'USD';
	const ledgerTotal = Number(pkg.invoice_reconciliation.ledger_final_cost_usd ?? 0);
	state.invoiceForm.total_amount = Number.isFinite(ledgerTotal) ? ledgerTotal : 0;
	state.invoiceForm.status = 'submitted';
	state.invoiceForm.notes = '';
}

export function normalizeCurrencyCode(value: string): string {
	const normalized = (value || '').trim().toUpperCase();
	return normalized || 'USD';
}
