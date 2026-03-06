import type {
	AcceptanceKpiMetric,
	IngestionSLAResponse,
	IntegrationAcceptanceEvidenceItem,
	IntegrationAcceptanceRun,
	JobSLOMetric,
	JobSLOResponse
} from './opsTypes';

export function buildIngestionSlaUrl(windowHours: number): string {
	const params = new URLSearchParams({
		window_hours: String(windowHours),
		target_success_rate_percent: '95'
	});
	return `/costs/ingestion/sla?${params.toString()}`;
}

export function buildJobSloUrl(windowHours: number): string {
	const params = new URLSearchParams({
		window_hours: String(windowHours),
		target_success_rate_percent: '95'
	});
	return `/jobs/slo?${params.toString()}`;
}

export function buildAcceptanceKpiUrl(
	startDate: string,
	endDate: string,
	ingestionWindowHours: number,
	responseFormat: 'json' | 'csv' = 'json'
): string {
	const params = new URLSearchParams({
		start_date: startDate,
		end_date: endDate,
		ingestion_window_hours: String(ingestionWindowHours),
		ingestion_target_success_rate_percent: '95',
		recency_target_hours: '48',
		chargeback_target_percent: '90',
		max_unit_anomalies: '0',
		response_format: responseFormat
	});
	return `/costs/acceptance/kpis?${params.toString()}`;
}

export function buildAcceptanceKpiCaptureUrl(
	startDate: string,
	endDate: string,
	ingestionWindowHours: number
): string {
	const params = new URLSearchParams({
		start_date: startDate,
		end_date: endDate,
		ingestion_window_hours: String(ingestionWindowHours),
		ingestion_target_success_rate_percent: '95',
		recency_target_hours: '48',
		chargeback_target_percent: '90',
		max_unit_anomalies: '0'
	});
	return `/costs/acceptance/kpis/capture?${params.toString()}`;
}

export function buildAcceptanceKpiHistoryUrl(limit = 50): string {
	const params = new URLSearchParams({ limit: String(limit) });
	return `/costs/acceptance/kpis/evidence?${params.toString()}`;
}

export function buildAcceptanceEvidenceUrl(limit = 100): string {
	const params = new URLSearchParams({ limit: String(limit) });
	return `/settings/notifications/acceptance-evidence?${params.toString()}`;
}

export function hasSelectedAcceptanceChannels(
	includeSlack: boolean,
	includeJira: boolean,
	includeWorkflow: boolean
): boolean {
	return includeSlack || includeJira || includeWorkflow;
}

export function buildClosePackageUrl(
	startDate: string,
	endDate: string,
	provider: string,
	responseFormat: 'json' | 'csv' = 'json',
	enforceFinalized = false
): string {
	const params = [
		`start_date=${encodeURIComponent(startDate)}`,
		`end_date=${encodeURIComponent(endDate)}`,
		`response_format=${encodeURIComponent(responseFormat)}`,
		`enforce_finalized=${encodeURIComponent(String(enforceFinalized))}`
	];
	if (provider !== 'all') {
		params.push(`provider=${encodeURIComponent(provider)}`);
	}
	return `/costs/reconciliation/close-package?${params.join('&')}`;
}

export function buildRestatementUrl(
	startDate: string,
	endDate: string,
	provider: string,
	responseFormat: 'json' | 'csv' = 'json'
): string {
	const params = [
		`start_date=${encodeURIComponent(startDate)}`,
		`end_date=${encodeURIComponent(endDate)}`,
		`response_format=${encodeURIComponent(responseFormat)}`
	];
	if (provider !== 'all') {
		params.push(`provider=${encodeURIComponent(provider)}`);
	}
	return `/costs/reconciliation/restatements?${params.join('&')}`;
}

export function formatDate(value: string | null): string {
	if (!value) return '-';
	return new Date(value).toLocaleString();
}

export function formatUsd(value: number): string {
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency: 'USD',
		maximumFractionDigits: 2
	}).format(value || 0);
}

export function formatNumber(value: number, fractionDigits = 2): string {
	return new Intl.NumberFormat('en-US', {
		maximumFractionDigits: fractionDigits
	}).format(value || 0);
}

export function formatDuration(seconds: number | null): string {
	if (seconds === null || Number.isNaN(seconds)) return '-';
	if (seconds < 60) return `${Math.round(seconds)}s`;
	const minutes = Math.floor(seconds / 60);
	const remainder = Math.round(seconds % 60);
	if (minutes < 60) return `${minutes}m ${remainder}s`;
	const hours = Math.floor(minutes / 60);
	const mins = minutes % 60;
	return `${hours}h ${mins}m`;
}

export function ingestionSlaBadgeClass(sla: IngestionSLAResponse): string {
	return sla.meets_sla ? 'badge badge-success' : 'badge badge-warning';
}

export function policyDecisionClass(decision: string | undefined): string {
	switch ((decision || '').toLowerCase()) {
		case 'allow':
			return 'badge badge-success';
		case 'warn':
			return 'badge badge-warning';
		case 'escalate':
			return 'badge badge-default';
		case 'block':
			return 'badge badge-error';
		default:
			return 'badge badge-default';
	}
}

export function acceptanceBadgeClass(metric: AcceptanceKpiMetric): string {
	if (!metric.available) return 'badge badge-default';
	return metric.meets_target ? 'badge badge-success' : 'badge badge-warning';
}

export function jobSloBadgeClass(slo: JobSLOResponse): string {
	return slo.overall_meets_slo ? 'badge badge-success' : 'badge badge-warning';
}

export function jobSloMetricBadgeClass(metric: JobSLOMetric): string {
	return metric.meets_slo ? 'badge badge-success' : 'badge badge-warning';
}

export function closeStatusBadgeClass(status: string | undefined): string {
	const normalized = (status || '').toLowerCase();
	if (normalized === 'ready') return 'badge badge-success';
	if (normalized.includes('blocked')) return 'badge badge-warning';
	return 'badge badge-default';
}

export function acceptanceRunStatusClass(status: string): string {
	const normalized = status.toLowerCase();
	if (normalized === 'success') return 'badge badge-success';
	if (normalized === 'partial_failure') return 'badge badge-warning';
	if (normalized === 'failed') return 'badge badge-error';
	return 'badge badge-default';
}

function toInt(value: unknown): number | null {
	if (typeof value === 'number' && Number.isFinite(value)) return Math.trunc(value);
	if (typeof value === 'string') {
		const parsed = Number.parseInt(value, 10);
		return Number.isNaN(parsed) ? null : parsed;
	}
	return null;
}

export function buildAcceptanceRuns(
	items: IntegrationAcceptanceEvidenceItem[]
): IntegrationAcceptanceRun[] {
	type RunBucket = {
		runId: string;
		suite: IntegrationAcceptanceEvidenceItem | null;
		channels: Record<string, IntegrationAcceptanceEvidenceItem>;
		latestTimestamp: string;
		actorEmail: string | null;
	};
	const buckets: Record<string, RunBucket> = {};

	for (const item of items) {
		const runId = (item.run_id || '').trim() || `single:${item.event_id}`;
		const existing = buckets[runId];
		const eventTs = Date.parse(item.event_timestamp);
		if (!existing) {
			buckets[runId] = {
				runId,
				suite:
					item.channel === 'suite' || item.event_type === 'integration_test.suite' ? item : null,
				channels: item.channel === 'suite' ? {} : { [item.channel]: item },
				latestTimestamp: item.event_timestamp,
				actorEmail: item.actor_email
			};
			continue;
		}

		const currentTs = Date.parse(existing.latestTimestamp);
		if (Number.isFinite(eventTs) && (!Number.isFinite(currentTs) || eventTs > currentTs)) {
			existing.latestTimestamp = item.event_timestamp;
		}
		if (!existing.actorEmail && item.actor_email) {
			existing.actorEmail = item.actor_email;
		}
		if (item.channel === 'suite' || item.event_type === 'integration_test.suite') {
			if (!existing.suite) {
				existing.suite = item;
			} else {
				const previousSuiteTs = Date.parse(existing.suite.event_timestamp);
				if (Number.isFinite(eventTs) && (!Number.isFinite(previousSuiteTs) || eventTs > previousSuiteTs)) {
					existing.suite = item;
				}
			}
		} else {
			const previousChannel = existing.channels[item.channel];
			if (!previousChannel) {
				existing.channels[item.channel] = item;
			} else {
				const previousChannelTs = Date.parse(previousChannel.event_timestamp);
				if (
					Number.isFinite(eventTs) &&
					(!Number.isFinite(previousChannelTs) || eventTs > previousChannelTs)
				) {
					existing.channels[item.channel] = item;
				}
			}
		}
	}

	return Object.values(buckets)
		.map((bucket) => {
			const channels = Object.values(bucket.channels)
				.map((entry) => ({
					channel: entry.channel,
					success: entry.success,
					statusCode: entry.status_code,
					message: entry.message,
					eventTimestamp: entry.event_timestamp
				}))
				.sort((a, b) => a.channel.localeCompare(b.channel));

			const fallbackPassed = channels.filter((channel) => channel.success).length;
			const fallbackFailed = channels.length - fallbackPassed;
			const suiteDetails = bucket.suite?.details || {};
			const checkedChannelsRaw = suiteDetails.checked_channels;
			const checkedChannels = Array.isArray(checkedChannelsRaw)
				? checkedChannelsRaw.map((value) => String(value))
				: channels.map((channel) => channel.channel);
			const passed = toInt(suiteDetails.passed) ?? fallbackPassed;
			const failed = toInt(suiteDetails.failed) ?? fallbackFailed;
			const rawOverallStatus =
				typeof suiteDetails.overall_status === 'string'
					? suiteDetails.overall_status.toLowerCase()
					: '';
			const overallStatus =
				rawOverallStatus || (failed === 0 ? 'success' : passed > 0 ? 'partial_failure' : 'failed');

			return {
				runId: bucket.runId,
				capturedAt: bucket.suite?.event_timestamp || bucket.latestTimestamp,
				overallStatus,
				passed,
				failed,
				checkedChannels,
				actorEmail: bucket.actorEmail,
				channels
			} satisfies IntegrationAcceptanceRun;
		})
		.sort((a, b) => {
			const left = Date.parse(a.capturedAt);
			const right = Date.parse(b.capturedAt);
			if (!Number.isFinite(left) && !Number.isFinite(right)) return 0;
			if (!Number.isFinite(left)) return 1;
			if (!Number.isFinite(right)) return -1;
			return right - left;
		});
}

export function parseFilenameFromDisposition(disposition: string | null, fallback: string): string {
	if (!disposition) return fallback;
	const match = disposition.match(/filename=\"?([^\"]+)\"?/i);
	if (!match || !match[1]) return fallback;
	return match[1];
}

export function downloadTextFile(filename: string, content: string, mime: string): void {
	if (typeof window === 'undefined' || typeof URL.createObjectURL !== 'function') {
		return;
	}
	const blob = new Blob([content], { type: mime });
	const url = URL.createObjectURL(blob);
	const link = document.createElement('a');
	link.href = url;
	link.download = filename;
	document.body.appendChild(link);
	link.click();
	link.remove();
	URL.revokeObjectURL(url);
}

export function normalizeCurrencyCode(value: string): string {
	const normalized = (value || '').trim().toUpperCase();
	return normalized || 'USD';
}
