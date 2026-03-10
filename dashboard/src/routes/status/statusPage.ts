export type StatusTone = 'success' | 'warning' | 'danger' | 'neutral';

export type StatusComponent = {
	name: string;
	statusLabel: string;
	tone: StatusTone;
	detail: string;
};

export type StatusSnapshot = {
	checkedAt: string;
	summaryLabel: string;
	summaryTone: StatusTone;
	summaryDetail: string;
	source: 'live' | 'fallback';
	components: StatusComponent[];
};

type BackendStatusComponent = {
	status?: string;
	error?: string;
	message?: string;
	response_code?: number;
	cpu_percent?: number;
	memory_percent?: number;
	disk_percent?: number;
	queue_depth?: number;
	services?: Record<string, BackendStatusComponent>;
};

export type BackendHealthPayload = {
	status?: string;
	timestamp?: string;
	database?: BackendStatusComponent;
	redis?: BackendStatusComponent;
	aws?: BackendStatusComponent;
	system?: BackendStatusComponent;
	checks?: {
		cache?: BackendStatusComponent;
		background_jobs?: BackendStatusComponent;
		system_resources?: BackendStatusComponent;
		external_services?: BackendStatusComponent;
	};
};

type NormalizedState = 'operational' | 'degraded' | 'unavailable' | 'not_configured' | 'unknown';

function normalizeState(rawStatus: string | undefined): NormalizedState {
	const status = String(rawStatus || '')
		.trim()
		.toLowerCase();
	if (['healthy', 'up', 'operational'].includes(status)) return 'operational';
	if (status === 'degraded') return 'degraded';
	if (['unhealthy', 'down', 'error'].includes(status)) return 'unavailable';
	if (['disabled', 'skipped'].includes(status)) return 'not_configured';
	return 'unknown';
}

function presentState(state: NormalizedState): { label: string; tone: StatusTone } {
	switch (state) {
		case 'operational':
			return { label: 'Operational', tone: 'success' };
		case 'degraded':
			return { label: 'Degraded', tone: 'warning' };
		case 'unavailable':
			return { label: 'Unavailable', tone: 'danger' };
		case 'not_configured':
			return { label: 'Not configured', tone: 'neutral' };
		default:
			return { label: 'Unknown', tone: 'neutral' };
	}
}

function buildComponent(name: string, state: NormalizedState, detail: string): StatusComponent {
	const presentation = presentState(state);
	return {
		name,
		statusLabel: presentation.label,
		tone: presentation.tone,
		detail
	};
}

function summarizeOverallStatus(
	status: string | undefined
): Pick<StatusSnapshot, 'summaryLabel' | 'summaryTone' | 'summaryDetail'> {
	switch (normalizeState(status)) {
		case 'operational':
			return {
				summaryLabel: 'Operational',
				summaryTone: 'success',
				summaryDetail: 'Core health checks are responding normally.'
			};
		case 'degraded':
			return {
				summaryLabel: 'Degraded',
				summaryTone: 'warning',
				summaryDetail:
					'Core health checks responded, but at least one dependency reported degradation.'
			};
		case 'unavailable':
			return {
				summaryLabel: 'Incident detected',
				summaryTone: 'danger',
				summaryDetail:
					'The health endpoint responded with an unhealthy state. Review the affected components below.'
			};
		default:
			return {
				summaryLabel: 'Status unavailable',
				summaryTone: 'neutral',
				summaryDetail:
					'A trusted automated health summary was not available at the time of this check.'
			};
	}
}

function statusDetail(
	component: BackendStatusComponent | undefined,
	defaults: Record<NormalizedState, string>
) {
	const state = normalizeState(component?.status);
	const problem = component?.message || component?.error;
	if (problem && state !== 'operational') {
		return problem;
	}
	if (component?.response_code && state === 'operational') {
		return `${defaults.operational} HTTP ${component.response_code}.`;
	}
	return defaults[state];
}

function buildLiveComponents(payload: BackendHealthPayload): StatusComponent[] {
	const externalServices = payload.checks?.external_services;
	const awsStatus = payload.aws ?? externalServices?.services?.aws_sts;
	const systemStatus = payload.system ?? payload.checks?.system_resources;

	return [
		buildComponent(
			'Platform API',
			normalizeState(payload.status),
			summarizeOverallStatus(payload.status).summaryDetail
		),
		buildComponent(
			'Database',
			normalizeState(payload.database?.status),
			statusDetail(payload.database, {
				operational: 'Primary database connectivity check passed.',
				degraded: 'Database is reachable, but the health check reported degraded behavior.',
				unavailable: 'Database connectivity is currently unavailable.',
				not_configured: 'Database health is not configured for this environment.',
				unknown: 'Database health could not be determined.'
			})
		),
		buildComponent(
			'Cache',
			normalizeState(payload.redis?.status),
			statusDetail(payload.redis, {
				operational: 'Cache health check completed successfully.',
				degraded: 'Cache is reachable, but the health check reported degraded behavior.',
				unavailable: 'Cache health check failed.',
				not_configured: 'Cache is not configured in this environment.',
				unknown: 'Cache health could not be determined.'
			})
		),
		buildComponent(
			'AWS reachability',
			normalizeState(awsStatus?.status),
			statusDetail(awsStatus, {
				operational: 'External AWS STS reachability check succeeded.',
				degraded: 'AWS STS reported degraded reachability during the last health check.',
				unavailable: 'AWS STS reachability check failed.',
				not_configured: 'External service checks are not configured for this environment.',
				unknown: 'AWS reachability could not be determined.'
			})
		),
		buildComponent(
			'Background jobs',
			normalizeState(payload.checks?.background_jobs?.status),
			statusDetail(payload.checks?.background_jobs, {
				operational: 'Background job processing checks are healthy.',
				degraded: 'Background jobs are running, but the health check reported degradation.',
				unavailable: 'Background job processing is currently unavailable.',
				not_configured: 'Background job monitoring is not configured for this environment.',
				unknown: 'Background job health could not be determined.'
			})
		),
		buildComponent(
			'System resources',
			normalizeState(systemStatus?.status),
			statusDetail(systemStatus, {
				operational: 'CPU, memory, and disk checks are within expected operating bounds.',
				degraded: 'System resources are under elevated pressure.',
				unavailable: 'System resource checks are currently unavailable.',
				not_configured: 'System resource monitoring is not configured for this environment.',
				unknown: 'System resource health could not be determined.'
			})
		)
	];
}

export function isBackendHealthPayload(value: unknown): value is BackendHealthPayload {
	if (typeof value !== 'object' || value === null) return false;
	const payload = value as Partial<BackendHealthPayload>;
	return typeof payload.status === 'string' || typeof payload.timestamp === 'string';
}

export function buildStatusSnapshot(payload: BackendHealthPayload): StatusSnapshot {
	const checkedAt =
		typeof payload.timestamp === 'string' && payload.timestamp.trim()
			? payload.timestamp
			: new Date().toISOString();
	const summary = summarizeOverallStatus(payload.status);

	return {
		checkedAt,
		summaryLabel: summary.summaryLabel,
		summaryTone: summary.summaryTone,
		summaryDetail: summary.summaryDetail,
		source: 'live',
		components: buildLiveComponents(payload)
	};
}

export function buildFallbackStatusSnapshot(reason: string): StatusSnapshot {
	const checkedAt = new Date().toISOString();
	return {
		checkedAt,
		summaryLabel: 'Status unavailable',
		summaryTone: 'neutral',
		summaryDetail: reason,
		source: 'fallback',
		components: [
			{
				name: 'Platform API',
				statusLabel: 'Unknown',
				tone: 'neutral',
				detail: reason
			},
			{
				name: 'Database',
				statusLabel: 'Unknown',
				tone: 'neutral',
				detail: 'A trusted automated database health summary was not available.'
			},
			{
				name: 'Cache',
				statusLabel: 'Unknown',
				tone: 'neutral',
				detail: 'A trusted automated cache health summary was not available.'
			},
			{
				name: 'AWS reachability',
				statusLabel: 'Unknown',
				tone: 'neutral',
				detail: 'A trusted external-service health summary was not available.'
			},
			{
				name: 'Background jobs',
				statusLabel: 'Unknown',
				tone: 'neutral',
				detail: 'A trusted background-job health summary was not available.'
			},
			{
				name: 'System resources',
				statusLabel: 'Unknown',
				tone: 'neutral',
				detail: 'A trusted system-resource health summary was not available.'
			}
		]
	};
}
