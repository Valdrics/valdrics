import { api } from '$lib/api';
import { edgeApiPath } from '$lib/edgeProxy';
import {
	buildClosePackageUrl,
	buildRestatementUrl,
	downloadTextFile,
	parseFilenameFromDisposition
} from './opsUtils';
import { hasInvalidUnitWindow } from './unitEconomics';
import {
	normalizeCurrencyCode,
	syncInvoiceFormFromClosePackage,
	type OpsOperationalState,
	type OpsRuntimeData
} from './opsOperationalState';

interface CloseActionsInput {
	getData: () => OpsRuntimeData | null | undefined;
	state: OpsOperationalState;
}

function hasSessionToken(data: OpsRuntimeData | null | undefined): data is OpsRuntimeData {
	return Boolean(data?.user && data.session?.access_token);
}

function buildHeaders(data: OpsRuntimeData): Record<string, string> {
	return {
		Authorization: `Bearer ${data.session?.access_token}`
	};
}

async function parseErrorMessage(response: Response, fallback: string): Promise<string> {
	const payload = await response.json().catch(() => ({}));
	const detail = (payload as { detail?: string; message?: string }).detail;
	const message = (payload as { detail?: string; message?: string }).message;
	return detail || message || fallback;
}

export function createOpsOperationalCloseActions(input: CloseActionsInput) {
	const { getData, state } = input;

	async function previewClosePackageInternal({
		silent = false
	}: {
		silent?: boolean;
	} = {}) {
		const data = getData();
		if (!hasSessionToken(data)) return;
		if (hasInvalidUnitWindow(state.closeStartDate, state.closeEndDate)) {
			state.error =
				'Close package date range is invalid: start date must be on or before end date.';
			return;
		}

		state.refreshingClosePackage = true;
		if (!silent) {
			state.error = '';
			state.success = '';
		}
		try {
			const headers = buildHeaders(data);
			const res = await api.get(
				edgeApiPath(
					buildClosePackageUrl(
						state.closeStartDate,
						state.closeEndDate,
						state.closeProvider,
						'json',
						false
					)
				),
				{ headers }
			);
			if (!res.ok) {
				throw new Error(await parseErrorMessage(res, 'Failed to load close package preview.'));
			}
			state.closePackage = await res.json();
			syncInvoiceFormFromClosePackage(state);
			if (!silent) {
				state.success = 'Close package preview refreshed.';
			}
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to refresh close package preview.';
		} finally {
			state.refreshingClosePackage = false;
		}
	}

	async function previewClosePackage() {
		await previewClosePackageInternal();
	}

	async function saveProviderInvoice(event?: SubmitEvent) {
		event?.preventDefault();
		const data = getData();
		if (!hasSessionToken(data)) return;
		if (state.closeProvider === 'all') {
			state.error =
				'Select a provider (AWS/Azure/GCP/SaaS/License/Platform/Hybrid) to store an invoice.';
			return;
		}
		if (hasInvalidUnitWindow(state.closeStartDate, state.closeEndDate)) {
			state.error = 'Invoice period is invalid: start date must be on or before end date.';
			return;
		}

		state.savingInvoice = true;
		state.error = '';
		state.success = '';
		try {
			const headers = buildHeaders(data);
			const payload = {
				provider: state.closeProvider,
				start_date: state.closeStartDate,
				end_date: state.closeEndDate,
				currency: normalizeCurrencyCode(state.invoiceForm.currency),
				total_amount: Number(state.invoiceForm.total_amount),
				invoice_number: state.invoiceForm.invoice_number.trim() || undefined,
				status: state.invoiceForm.status.trim() || undefined,
				notes: state.invoiceForm.notes.trim() || undefined
			};
			const res = await api.post(edgeApiPath('/costs/reconciliation/invoices'), payload, {
				headers
			});
			if (!res.ok) {
				throw new Error(await parseErrorMessage(res, 'Failed to save provider invoice.'));
			}
			await res.json().catch(() => null);
			await previewClosePackageInternal({ silent: true });
			state.success = 'Invoice saved.';
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to save provider invoice.';
		} finally {
			state.savingInvoice = false;
		}
	}

	async function deleteProviderInvoice() {
		const data = getData();
		if (!hasSessionToken(data)) return;
		const invoiceId = state.closePackage?.invoice_reconciliation?.invoice?.id;
		if (!invoiceId) {
			return;
		}

		state.deletingInvoice = true;
		state.error = '';
		state.success = '';
		try {
			const headers = buildHeaders(data);
			const res = await api.delete(
				edgeApiPath(`/costs/reconciliation/invoices/${encodeURIComponent(invoiceId)}`),
				{ headers }
			);
			if (!res.ok) {
				throw new Error(await parseErrorMessage(res, 'Failed to delete provider invoice.'));
			}
			await res.json().catch(() => null);
			await previewClosePackageInternal({ silent: true });
			state.success = 'Invoice deleted.';
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to delete provider invoice.';
		} finally {
			state.deletingInvoice = false;
		}
	}

	async function downloadClosePackageJson() {
		const data = getData();
		if (!hasSessionToken(data) || state.downloadingCloseJson) return;
		state.downloadingCloseJson = true;
		state.error = '';
		state.success = '';
		try {
			if (hasInvalidUnitWindow(state.closeStartDate, state.closeEndDate)) {
				throw new Error(
					'Close package date range is invalid: start date must be on or before end date.'
				);
			}
			const headers = buildHeaders(data);
			const res = await api.get(
				edgeApiPath(
					buildClosePackageUrl(
						state.closeStartDate,
						state.closeEndDate,
						state.closeProvider,
						'json',
						false
					)
				),
				{ headers }
			);
			if (!res.ok) {
				throw new Error(await parseErrorMessage(res, 'Failed to fetch close package JSON.'));
			}
			state.closePackage = await res.json();
			syncInvoiceFormFromClosePackage(state);
			const filename = `close-package-${state.closeStartDate}-${state.closeEndDate}-${state.closeProvider}.json`;
			downloadTextFile(filename, JSON.stringify(state.closePackage, null, 2), 'application/json');
			state.success = 'Close package JSON downloaded.';
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to export close package JSON.';
		} finally {
			state.downloadingCloseJson = false;
		}
	}

	async function downloadClosePackageCsv() {
		const data = getData();
		if (!hasSessionToken(data) || state.downloadingCloseCsv) return;
		state.downloadingCloseCsv = true;
		state.error = '';
		state.success = '';
		try {
			if (hasInvalidUnitWindow(state.closeStartDate, state.closeEndDate)) {
				throw new Error(
					'Close package date range is invalid: start date must be on or before end date.'
				);
			}
			const headers = buildHeaders(data);
			const res = await api.get(
				edgeApiPath(
					buildClosePackageUrl(
						state.closeStartDate,
						state.closeEndDate,
						state.closeProvider,
						'csv',
						false
					)
				),
				{ headers }
			);
			if (!res.ok) {
				throw new Error(await parseErrorMessage(res, 'Failed to export close package CSV.'));
			}
			const content = await res.text();
			const filename = parseFilenameFromDisposition(
				res.headers.get('content-disposition'),
				`close-package-${state.closeStartDate}-${state.closeEndDate}-${state.closeProvider}.csv`
			);
			downloadTextFile(filename, content, 'text/csv');
			state.success = 'Close package CSV downloaded.';
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to export close package CSV.';
		} finally {
			state.downloadingCloseCsv = false;
		}
	}

	async function downloadRestatementCsv() {
		const data = getData();
		if (!hasSessionToken(data) || state.downloadingRestatementCsv) return;
		state.downloadingRestatementCsv = true;
		state.error = '';
		state.success = '';
		try {
			if (hasInvalidUnitWindow(state.closeStartDate, state.closeEndDate)) {
				throw new Error(
					'Close package date range is invalid: start date must be on or before end date.'
				);
			}
			const headers = buildHeaders(data);
			const res = await api.get(
				edgeApiPath(
					buildRestatementUrl(state.closeStartDate, state.closeEndDate, state.closeProvider, 'csv')
				),
				{ headers }
			);
			if (!res.ok) {
				throw new Error(await parseErrorMessage(res, 'Failed to export restatements CSV.'));
			}
			const content = await res.text();
			const filename = parseFilenameFromDisposition(
				res.headers.get('content-disposition'),
				`restatements-${state.closeStartDate}-${state.closeEndDate}-${state.closeProvider}.csv`
			);
			downloadTextFile(filename, content, 'text/csv');
			state.success = 'Restatements CSV downloaded.';
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to export restatements CSV.';
		} finally {
			state.downloadingRestatementCsv = false;
		}
	}

	return {
		previewClosePackage,
		saveProviderInvoice,
		deleteProviderInvoice,
		downloadClosePackageJson,
		downloadClosePackageCsv,
		downloadRestatementCsv
	};
}
