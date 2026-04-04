import { api } from '$lib/api';
import { edgeApiPath } from '$lib/edgeProxy';
import { TimeoutError } from '$lib/fetchWithTimeout';
import { buildIngestionSlaUrl, buildJobSloUrl } from './opsUtils';
import type { OpsOperationalState, OpsRuntimeData } from './opsOperationalState';
import type { IngestionSLAResponse, JobSLOResponse } from './opsTypes';

interface ReliabilityActionsInput {
	getData: () => OpsRuntimeData | null | undefined;
	state: OpsOperationalState;
	requestTimeoutMs: number;
	access: {
		jobSlo: () => boolean;
	};
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

export function createOpsOperationalReliabilityActions(input: ReliabilityActionsInput) {
	const { getData, state, requestTimeoutMs, access } = input;

	async function loadReliabilityData({ silent = true }: { silent?: boolean } = {}) {
		const data = getData();
		if (!hasSessionToken(data)) {
			return;
		}

		try {
			const headers = buildHeaders(data);
			const results = await Promise.allSettled([
				getWithTimeout(
					edgeApiPath(buildIngestionSlaUrl(state.ingestionSlaWindowHours)),
					headers,
					requestTimeoutMs
				),
				access.jobSlo()
					? getWithTimeout(
							edgeApiPath(buildJobSloUrl(state.jobSloWindowHours)),
							headers,
							requestTimeoutMs
						)
					: Promise.resolve(null)
			]);

			const responseOrNull = (index: number): Response | null =>
				results[index]?.status === 'fulfilled'
					? (results[index] as PromiseFulfilledResult<Response>).value
					: null;

			const ingestionSlaRes = responseOrNull(0);
			const jobSloRes = responseOrNull(1);

			state.ingestionSla = ingestionSlaRes?.ok
				? ((await ingestionSlaRes.json()) as IngestionSLAResponse)
				: null;
			state.jobSlo = jobSloRes?.ok ? ((await jobSloRes.json()) as JobSLOResponse) : null;

			const timedOutCount = results.filter(
				(result) => result.status === 'rejected' && result.reason instanceof TimeoutError
			).length;
			if (timedOutCount > 0 && !silent) {
				state.error = `${timedOutCount} reliability widgets timed out. You can refresh individual sections.`;
			}
		} catch (error) {
			if (!silent) {
				const err = error as Error;
				state.error = err.message || 'Failed to load reliability widgets.';
			}
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

	return {
		loadReliabilityData,
		refreshIngestionSla,
		refreshJobSlo
	};
}
