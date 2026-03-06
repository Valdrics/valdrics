import { api } from '$lib/api';
import { edgeApiPath } from '$lib/edgeProxy';
import { TimeoutError } from '$lib/fetchWithTimeout';
import {
	buildAcceptanceEvidenceUrl,
	buildAcceptanceKpiHistoryUrl,
	buildAcceptanceKpiUrl,
	buildClosePackageUrl,
	buildIngestionSlaUrl,
	buildJobSloUrl,
	buildAcceptanceRuns
} from './opsUtils';
import {
	buildUnitEconomicsUrl,
	hasInvalidUnitWindow
} from './unitEconomics';
import {
	syncInvoiceFormFromClosePackage,
	type OpsOperationalState,
	type OpsRuntimeData
} from './opsOperationalState';
import type {
	AcceptanceKpiEvidenceResponse,
	IngestionSLAResponse,
	IntegrationAcceptanceEvidenceResponse,
	JobSLOResponse,
	UnitEconomicsResponse,
	UnitEconomicsSettings
} from './opsTypes';

const EDGE_API_BASE = edgeApiPath('').replace(/\/$/, '');

interface CoreActionsInput {
	getData: () => OpsRuntimeData | null | undefined;
	state: OpsOperationalState;
	requestTimeoutMs: number;
}

function hasSessionToken(data: OpsRuntimeData | null | undefined): data is OpsRuntimeData {
	return Boolean(data?.user && data.session?.access_token);
}

function buildHeaders(data: OpsRuntimeData): Record<string, string> {
	return {
		Authorization: `Bearer ${data.session?.access_token}`
	};
}

async function getWithTimeout(
	url: string,
	headers: Record<string, string>,
	timeoutMs: number
): Promise<Response> {
	return api.get(url, { headers, timeoutMs });
}

async function parseErrorMessage(response: Response, fallback: string): Promise<string> {
	const payload = await response.json().catch(() => ({}));
	const detail = (payload as { detail?: string; message?: string }).detail;
	const message = (payload as { detail?: string; message?: string }).message;
	return detail || message || fallback;
}

export function createOpsOperationalCoreActions(input: CoreActionsInput) {
	const { getData, state, requestTimeoutMs } = input;

	async function loadOperationalData() {
		const data = getData();
		if (!hasSessionToken(data)) {
			return;
		}
		if (hasInvalidUnitWindow(state.unitStartDate, state.unitEndDate)) {
			state.error = 'Unit economics date range is invalid: start date must be on or before end date.';
			return;
		}

		state.error = '';
		try {
			const headers = buildHeaders(data);
			const results = await Promise.allSettled([
				getWithTimeout(edgeApiPath('/costs/unit-economics/settings'), headers, requestTimeoutMs),
				getWithTimeout(
					buildUnitEconomicsUrl(
						EDGE_API_BASE,
						state.unitStartDate,
						state.unitEndDate,
						state.unitAlertOnAnomaly
					),
					headers,
					requestTimeoutMs
				),
				getWithTimeout(
					edgeApiPath(buildIngestionSlaUrl(state.ingestionSlaWindowHours)),
					headers,
					requestTimeoutMs
				),
				getWithTimeout(edgeApiPath(buildJobSloUrl(state.jobSloWindowHours)), headers, requestTimeoutMs),
				getWithTimeout(
					edgeApiPath(
						buildAcceptanceKpiUrl(
							state.unitStartDate,
							state.unitEndDate,
							state.ingestionSlaWindowHours
						)
					),
					headers,
					requestTimeoutMs
				),
				getWithTimeout(edgeApiPath(buildAcceptanceKpiHistoryUrl(25)), headers, requestTimeoutMs),
				getWithTimeout(
					edgeApiPath(
						buildClosePackageUrl(
							state.closeStartDate,
							state.closeEndDate,
							state.closeProvider,
							'json',
							false
						)
					),
					headers,
					requestTimeoutMs
				),
				getWithTimeout(edgeApiPath(buildAcceptanceEvidenceUrl()), headers, requestTimeoutMs)
			]);

			const responseOrNull = (index: number): Response | null =>
				results[index]?.status === 'fulfilled'
					? (results[index] as PromiseFulfilledResult<Response>).value
					: null;

			const settingsRes = responseOrNull(0);
			const unitRes = responseOrNull(1);
			const ingestionSlaRes = responseOrNull(2);
			const jobSloRes = responseOrNull(3);
			const acceptanceRes = responseOrNull(4);
			const acceptanceHistoryRes = responseOrNull(5);
			const closePackageRes = responseOrNull(6);
			const acceptanceEvidenceRes = responseOrNull(7);

			state.unitSettings = settingsRes?.ok
				? ((await settingsRes.json()) as UnitEconomicsSettings)
				: null;
			state.unitEconomics = unitRes?.ok ? ((await unitRes.json()) as UnitEconomicsResponse) : null;
			state.ingestionSla = ingestionSlaRes?.ok
				? ((await ingestionSlaRes.json()) as IngestionSLAResponse)
				: null;
			state.jobSlo = jobSloRes?.ok ? ((await jobSloRes.json()) as JobSLOResponse) : null;
			state.acceptanceKpis = acceptanceRes?.ok ? await acceptanceRes.json() : null;

			const acceptanceHistoryPayload = acceptanceHistoryRes?.ok
				? ((await acceptanceHistoryRes.json()) as AcceptanceKpiEvidenceResponse)
				: null;
			state.acceptanceKpiHistory = acceptanceHistoryPayload?.items || [];

			state.closePackage = closePackageRes?.ok ? await closePackageRes.json() : null;
			if (state.closePackage) {
				syncInvoiceFormFromClosePackage(state);
			}

			const acceptanceEvidencePayload = acceptanceEvidenceRes?.ok
				? ((await acceptanceEvidenceRes.json()) as IntegrationAcceptanceEvidenceResponse)
				: null;
			state.acceptanceRuns = buildAcceptanceRuns(acceptanceEvidencePayload?.items || []);

			const timedOutCount = results.filter(
				(result) => result.status === 'rejected' && result.reason instanceof TimeoutError
			).length;
			if (timedOutCount > 0) {
				state.error = `${timedOutCount} Ops widgets timed out. You can refresh individual sections.`;
			}
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to load operations widgets.';
		}
	}

	async function refreshUnitEconomics() {
		const data = getData();
		if (!hasSessionToken(data)) return;
		if (hasInvalidUnitWindow(state.unitStartDate, state.unitEndDate)) {
			state.error = 'Unit economics date range is invalid: start date must be on or before end date.';
			return;
		}

		state.refreshingUnitEconomics = true;
		state.error = '';
		state.success = '';
		try {
			const headers = buildHeaders(data);
			const [settingsRes, unitRes] = await Promise.all([
				api.get(edgeApiPath('/costs/unit-economics/settings'), { headers }),
				api.get(
					buildUnitEconomicsUrl(
						EDGE_API_BASE,
						state.unitStartDate,
						state.unitEndDate,
						state.unitAlertOnAnomaly
					),
					{ headers }
				)
			]);

			if (!unitRes.ok) {
				throw new Error(await parseErrorMessage(unitRes, 'Failed to load unit economics metrics.'));
			}
			state.unitEconomics = await unitRes.json();
			if (settingsRes.ok) {
				state.unitSettings = await settingsRes.json();
			}
			state.success = 'Unit economics refreshed.';
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to refresh unit economics.';
		} finally {
			state.refreshingUnitEconomics = false;
		}
	}

	async function refreshIngestionSla() {
		const data = getData();
		if (!hasSessionToken(data)) return;
		state.refreshingIngestionSla = true;
		state.error = '';
		state.success = '';
		try {
			const headers = buildHeaders(data);
			const res = await api.get(edgeApiPath(buildIngestionSlaUrl(state.ingestionSlaWindowHours)), {
				headers
			});
			if (!res.ok) {
				throw new Error(await parseErrorMessage(res, 'Failed to load ingestion SLA.'));
			}
			state.ingestionSla = await res.json();
			state.success = 'Ingestion SLA refreshed.';
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to refresh ingestion SLA.';
		} finally {
			state.refreshingIngestionSla = false;
		}
	}

	async function refreshJobSlo() {
		const data = getData();
		if (!hasSessionToken(data)) return;
		state.refreshingJobSlo = true;
		state.error = '';
		state.success = '';
		try {
			const headers = buildHeaders(data);
			const res = await api.get(edgeApiPath(buildJobSloUrl(state.jobSloWindowHours)), { headers });
			if (!res.ok) {
				throw new Error(await parseErrorMessage(res, 'Failed to load job SLO metrics.'));
			}
			state.jobSlo = await res.json();
			state.success = 'Job SLO metrics refreshed.';
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to refresh job SLO metrics.';
		} finally {
			state.refreshingJobSlo = false;
		}
	}

	async function saveUnitEconomicsSettings(event?: SubmitEvent) {
		event?.preventDefault();
		const data = getData();
		if (!state.unitSettings || !hasSessionToken(data)) {
			return;
		}

		state.savingUnitSettings = true;
		state.error = '';
		state.success = '';
		try {
			const headers = buildHeaders(data);
			const payload = {
				default_request_volume: Number(state.unitSettings.default_request_volume),
				default_workload_volume: Number(state.unitSettings.default_workload_volume),
				default_customer_volume: Number(state.unitSettings.default_customer_volume),
				anomaly_threshold_percent: Number(state.unitSettings.anomaly_threshold_percent)
			};
			const res = await api.put(edgeApiPath('/costs/unit-economics/settings'), payload, { headers });
			if (!res.ok) {
				throw new Error(
					await parseErrorMessage(
						res,
						'Failed to save unit economics defaults. Admin role is required.'
					)
				);
			}
			state.unitSettings = await res.json();
			state.success = 'Unit economics defaults saved.';
			await refreshUnitEconomics();
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to save unit economics defaults.';
		} finally {
			state.savingUnitSettings = false;
		}
	}

	return {
		loadOperationalData,
		refreshUnitEconomics,
		refreshIngestionSla,
		refreshJobSlo,
		saveUnitEconomicsSettings
	};
}
