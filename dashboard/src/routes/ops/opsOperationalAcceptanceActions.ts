import { api } from '$lib/api';
import { edgeApiPath } from '$lib/edgeProxy';
import {
	acceptanceRunStatusClass,
	buildAcceptanceEvidenceUrl,
	buildAcceptanceKpiCaptureUrl,
	buildAcceptanceKpiHistoryUrl,
	buildAcceptanceKpiUrl,
	buildAcceptanceRuns,
	downloadTextFile,
	hasSelectedAcceptanceChannels,
	parseFilenameFromDisposition
} from './opsUtils';
import { hasInvalidUnitWindow } from './unitEconomics';
import type {
	AcceptanceKpiCaptureResponse,
	AcceptanceKpiEvidenceResponse,
	IntegrationAcceptanceCaptureResponse,
	IntegrationAcceptanceEvidenceResponse
} from './opsTypes';
import type { OpsOperationalState, OpsRuntimeData } from './opsOperationalState';

interface AcceptanceActionsInput {
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

export function createOpsOperationalAcceptanceActions(input: AcceptanceActionsInput) {
	const { getData, state } = input;

	async function refreshAcceptanceKpis() {
		const data = getData();
		if (!hasSessionToken(data)) return;
		if (hasInvalidUnitWindow(state.unitStartDate, state.unitEndDate)) {
			state.error = 'Unit economics date range is invalid: start date must be on or before end date.';
			return;
		}

		state.refreshingAcceptanceKpis = true;
		state.error = '';
		state.success = '';
		try {
			const headers = buildHeaders(data);
			const res = await api.get(
				edgeApiPath(
					buildAcceptanceKpiUrl(
						state.unitStartDate,
						state.unitEndDate,
						state.ingestionSlaWindowHours
					)
				),
				{ headers }
			);
			if (!res.ok) {
				throw new Error(await parseErrorMessage(res, 'Failed to load acceptance KPIs.'));
			}
			state.acceptanceKpis = await res.json();
			state.success = 'Acceptance KPI evidence refreshed.';
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to refresh acceptance KPIs.';
		} finally {
			state.refreshingAcceptanceKpis = false;
		}
	}

	async function refreshAcceptanceKpiHistory() {
		const data = getData();
		if (!hasSessionToken(data)) return;
		state.refreshingAcceptanceKpiHistory = true;
		state.error = '';
		state.success = '';
		try {
			const headers = buildHeaders(data);
			const res = await api.get(edgeApiPath(buildAcceptanceKpiHistoryUrl(50)), { headers });
			if (!res.ok) {
				throw new Error(await parseErrorMessage(res, 'Failed to load acceptance KPI history.'));
			}
			const payload = (await res.json()) as AcceptanceKpiEvidenceResponse;
			state.acceptanceKpiHistory = payload.items || [];
			state.success = 'Acceptance KPI evidence history refreshed.';
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to refresh acceptance KPI history.';
		} finally {
			state.refreshingAcceptanceKpiHistory = false;
		}
	}

	async function captureAcceptanceKpis() {
		const data = getData();
		if (!hasSessionToken(data)) return;
		if (hasInvalidUnitWindow(state.unitStartDate, state.unitEndDate)) {
			state.error = 'Acceptance KPI date range is invalid: start date must be on or before end date.';
			return;
		}

		state.capturingAcceptanceKpis = true;
		state.error = '';
		state.success = '';
		try {
			const headers = buildHeaders(data);
			const res = await api.post(
				edgeApiPath(
					buildAcceptanceKpiCaptureUrl(
						state.unitStartDate,
						state.unitEndDate,
						state.ingestionSlaWindowHours
					)
				),
				undefined,
				{ headers }
			);
			if (!res.ok) {
				throw new Error(await parseErrorMessage(res, 'Failed to capture acceptance KPI evidence.'));
			}
			const payload = (await res.json()) as AcceptanceKpiCaptureResponse;
			state.lastAcceptanceKpiCapture = payload;
			state.acceptanceKpis = payload.acceptance_kpis;
			state.success = 'Acceptance KPI evidence captured.';
			void refreshAcceptanceKpiHistory();
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to capture acceptance KPI evidence.';
		} finally {
			state.capturingAcceptanceKpis = false;
		}
	}

	async function refreshAcceptanceRuns() {
		const data = getData();
		if (!hasSessionToken(data)) return;
		state.refreshingAcceptanceRuns = true;
		state.error = '';
		state.success = '';
		try {
			const headers = buildHeaders(data);
			const res = await api.get(edgeApiPath(buildAcceptanceEvidenceUrl()), { headers });
			if (!res.ok) {
				throw new Error(await parseErrorMessage(res, 'Failed to load integration acceptance runs.'));
			}
			const payload = (await res.json()) as IntegrationAcceptanceEvidenceResponse;
			state.acceptanceRuns = buildAcceptanceRuns(payload.items || []);
			state.success = 'Integration acceptance evidence refreshed.';
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to refresh integration acceptance evidence.';
		} finally {
			state.refreshingAcceptanceRuns = false;
		}
	}

	async function captureAcceptanceRuns() {
		const data = getData();
		if (!hasSessionToken(data)) return;
		if (
			!hasSelectedAcceptanceChannels(
				state.captureIncludeSlack,
				state.captureIncludeJira,
				state.captureIncludeWorkflow
			)
		) {
			state.error = 'Select at least one integration channel (Slack, Jira, or Workflow).';
			state.success = '';
			return;
		}

		state.capturingAcceptanceRuns = true;
		state.error = '';
		state.success = '';
		try {
			const headers = buildHeaders(data);
			const res = await api.post(
				edgeApiPath('/settings/notifications/acceptance-evidence/capture'),
				{
					include_slack: state.captureIncludeSlack,
					include_jira: state.captureIncludeJira,
					include_workflow: state.captureIncludeWorkflow,
					fail_fast: state.captureFailFast
				},
				{ headers }
			);
			if (!res.ok) {
				throw new Error(await parseErrorMessage(res, 'Failed to capture integration acceptance run.'));
			}
			const payload = (await res.json()) as IntegrationAcceptanceCaptureResponse;
			state.lastAcceptanceCapture = payload;
			await refreshAcceptanceRuns();
			state.success = `Integration acceptance run captured (${payload.run_id.slice(0, 8)}...) - ${payload.passed} passed / ${payload.failed} failed.`;
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to capture integration acceptance run.';
		} finally {
			state.capturingAcceptanceRuns = false;
		}
	}

	async function captureAcceptanceKpisOrThrow(data: OpsRuntimeData): Promise<AcceptanceKpiCaptureResponse> {
		const headers = buildHeaders(data);
		const res = await api.post(
			edgeApiPath(
				buildAcceptanceKpiCaptureUrl(
					state.unitStartDate,
					state.unitEndDate,
					state.ingestionSlaWindowHours
				)
			),
			undefined,
			{ headers }
		);
		if (!res.ok) {
			throw new Error(await parseErrorMessage(res, 'Failed to capture acceptance KPI evidence.'));
		}
		return (await res.json()) as AcceptanceKpiCaptureResponse;
	}

	async function captureIntegrationAcceptanceOrThrow(
		data: OpsRuntimeData
	): Promise<IntegrationAcceptanceCaptureResponse> {
		const headers = buildHeaders(data);
		const res = await api.post(
			edgeApiPath('/settings/notifications/acceptance-evidence/capture'),
			{
				include_slack: state.captureIncludeSlack,
				include_jira: state.captureIncludeJira,
				include_workflow: state.captureIncludeWorkflow,
				fail_fast: state.captureFailFast
			},
			{ headers }
		);
		if (!res.ok) {
			throw new Error(
				await parseErrorMessage(res, 'Failed to capture integration acceptance evidence.')
			);
		}
		return (await res.json()) as IntegrationAcceptanceCaptureResponse;
	}

	async function runAcceptanceSuite() {
		const data = getData();
		if (!hasSessionToken(data)) return;
		if (hasInvalidUnitWindow(state.unitStartDate, state.unitEndDate)) {
			state.error = 'Acceptance KPI date range is invalid: start date must be on or before end date.';
			return;
		}
		if (
			!hasSelectedAcceptanceChannels(
				state.captureIncludeSlack,
				state.captureIncludeJira,
				state.captureIncludeWorkflow
			)
		) {
			state.error = 'Select at least one integration channel (Slack, Jira, or Workflow).';
			state.success = '';
			return;
		}

		state.runningAcceptanceSuite = true;
		state.error = '';
		state.success = '';
		try {
			state.capturingAcceptanceKpis = true;
			const kpiPayload = await captureAcceptanceKpisOrThrow(data);
			state.lastAcceptanceKpiCapture = kpiPayload;
			state.acceptanceKpis = kpiPayload.acceptance_kpis;
			await refreshAcceptanceKpiHistory();
			state.capturingAcceptanceKpis = false;

			state.capturingAcceptanceRuns = true;
			const integrationPayload = await captureIntegrationAcceptanceOrThrow(data);
			state.lastAcceptanceCapture = integrationPayload;
			await refreshAcceptanceRuns();
			state.capturingAcceptanceRuns = false;

			state.success = `Acceptance suite captured: KPIs (${kpiPayload.event_id.slice(0, 8)}...) + integrations (${integrationPayload.run_id.slice(0, 8)}...)`;
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to run acceptance suite.';
		} finally {
			state.capturingAcceptanceKpis = false;
			state.capturingAcceptanceRuns = false;
			state.runningAcceptanceSuite = false;
		}
	}

	async function downloadAcceptanceKpiJson() {
		if (state.downloadingAcceptanceJson) {
			return;
		}
		state.downloadingAcceptanceJson = true;
		state.error = '';
		state.success = '';
		try {
			if (!state.acceptanceKpis) {
				await refreshAcceptanceKpis();
			}
			if (!state.acceptanceKpis) {
				throw new Error('No acceptance KPI data available to export.');
			}
			const filename = `acceptance-kpis-${state.acceptanceKpis.start_date}-${state.acceptanceKpis.end_date}.json`;
			downloadTextFile(filename, JSON.stringify(state.acceptanceKpis, null, 2), 'application/json');
			state.success = 'Acceptance KPI JSON downloaded.';
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to export acceptance KPI JSON.';
		} finally {
			state.downloadingAcceptanceJson = false;
		}
	}

	async function downloadAcceptanceKpiCsv() {
		const data = getData();
		if (!hasSessionToken(data) || state.downloadingAcceptanceCsv) return;
		state.downloadingAcceptanceCsv = true;
		state.error = '';
		state.success = '';
		try {
			const headers = buildHeaders(data);
			const res = await api.get(
				edgeApiPath(
					buildAcceptanceKpiUrl(
						state.unitStartDate,
						state.unitEndDate,
						state.ingestionSlaWindowHours,
						'csv'
					)
				),
				{ headers }
			);
			if (!res.ok) {
				throw new Error(await parseErrorMessage(res, 'Failed to export acceptance KPI CSV.'));
			}
			const content = await res.text();
			const filename = parseFilenameFromDisposition(
				res.headers.get('content-disposition'),
				`acceptance-kpis-${state.unitStartDate}-${state.unitEndDate}.csv`
			);
			downloadTextFile(filename, content, 'text/csv');
			state.success = 'Acceptance KPI CSV downloaded.';
		} catch (error) {
			const err = error as Error;
			state.error = err.message || 'Failed to export acceptance KPI CSV.';
		} finally {
			state.downloadingAcceptanceCsv = false;
		}
	}

	return {
		refreshAcceptanceKpis,
		refreshAcceptanceKpiHistory,
		captureAcceptanceKpis,
		refreshAcceptanceRuns,
		captureAcceptanceRuns,
		runAcceptanceSuite,
		downloadAcceptanceKpiJson,
		downloadAcceptanceKpiCsv,
		hasSelectedAcceptanceChannels,
		acceptanceRunStatusClass
	};
}
