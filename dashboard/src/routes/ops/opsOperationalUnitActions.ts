import { api } from '$lib/api';
import { edgeApiPath } from '$lib/edgeProxy';
import { TimeoutError } from '$lib/fetchWithTimeout';
import { buildUnitEconomicsUrl, hasInvalidUnitWindow } from './unitEconomics';
import type { OpsOperationalState, OpsRuntimeData } from './opsOperationalState';
import type { UnitEconomicsResponse, UnitEconomicsSettings } from './opsTypes';

const EDGE_API_BASE = edgeApiPath('').replace(/\/$/, '');

interface UnitActionsInput {
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

export function createOpsOperationalUnitActions(input: UnitActionsInput) {
	const { getData, state, requestTimeoutMs } = input;

	async function loadPrimaryOperationalData() {
		const data = getData();
		if (!hasSessionToken(data)) {
			return;
		}
		if (hasInvalidUnitWindow(state.unitStartDate, state.unitEndDate)) {
			state.error =
				'Unit economics date range is invalid: start date must be on or before end date.';
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
				)
			]);

			const responseOrNull = (index: number): Response | null =>
				results[index]?.status === 'fulfilled'
					? (results[index] as PromiseFulfilledResult<Response>).value
					: null;

			const settingsRes = responseOrNull(0);
			const unitRes = responseOrNull(1);

			state.unitSettings = settingsRes?.ok
				? ((await settingsRes.json()) as UnitEconomicsSettings)
				: null;
			state.unitEconomics = unitRes?.ok ? ((await unitRes.json()) as UnitEconomicsResponse) : null;

			const timedOutCount = results.filter(
				(result) => result.status === 'rejected' && result.reason instanceof TimeoutError
			).length;
			if (timedOutCount > 0) {
				state.error = `${timedOutCount} Ops widgets timed out. You can refresh unit economics.`;
			}
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to load unit economics widgets.';
		}
	}

	async function refreshUnitEconomics() {
		const data = getData();
		if (!hasSessionToken(data)) return;
		if (hasInvalidUnitWindow(state.unitStartDate, state.unitEndDate)) {
			state.error =
				'Unit economics date range is invalid: start date must be on or before end date.';
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
			const res = await api.put(edgeApiPath('/costs/unit-economics/settings'), payload, {
				headers
			});
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
		loadPrimaryOperationalData,
		refreshUnitEconomics,
		saveUnitEconomicsSettings
	};
}
