import { edgeApiPath } from '$lib/edgeProxy';

export type CampaignRow = {
	utm_source: string;
	utm_medium: string;
	utm_campaign: string;
	total_events: number;
	cta_events: number;
	signup_intent_events: number;
	onboarded_tenants: number;
	connected_tenants: number;
	first_value_tenants: number;
	pql_tenants: number;
	pricing_view_tenants: number;
	checkout_started_tenants: number;
	paid_tenants: number;
	first_seen_at: string | null;
	last_seen_at: string | null;
};

export type WeeklyWindowSummary = {
	total_events: number;
	cta_events: number;
	signup_intent_events: number;
	onboarded_tenants: number;
	connected_tenants: number;
	first_value_tenants: number;
	pql_tenants: number;
	pricing_view_tenants: number;
	checkout_started_tenants: number;
	paid_tenants: number;
	signup_to_connection_rate: number | null;
	connection_to_first_value_rate: number | null;
};

export type WeeklyWindowDelta = {
	total_events: number;
	signup_intent_events: number;
	onboarded_tenants: number;
	connected_tenants: number;
	first_value_tenants: number;
	pql_tenants: number;
	pricing_view_tenants: number;
	checkout_started_tenants: number;
	paid_tenants: number;
	signup_to_connection_rate: number | null;
	connection_to_first_value_rate: number | null;
};

export type FunnelHealthAlert = {
	key: string;
	label: string;
	status: 'healthy' | 'watch' | 'critical' | 'insufficient_data';
	threshold_rate: number;
	current_rate: number | null;
	previous_rate: number | null;
	weekly_delta: number | null;
	current_numerator: number;
	current_denominator: number;
	message: string;
};

export type CampaignMetricsResponse = {
	window_start: string;
	window_end: string;
	days: number;
	total_events: number;
	total_onboarded_tenants: number;
	total_connected_tenants: number;
	total_first_value_tenants: number;
	total_pql_tenants: number;
	total_pricing_view_tenants: number;
	total_checkout_started_tenants: number;
	total_paid_tenants: number;
	weekly_current: WeeklyWindowSummary;
	weekly_previous: WeeklyWindowSummary;
	weekly_delta: WeeklyWindowDelta;
	funnel_alerts: FunnelHealthAlert[];
	items: CampaignRow[];
};

export const LANDING_CAMPAIGN_REQUEST_TIMEOUT_MS = 10000;
const QUERY_LIMIT = 100;

export function formatCampaignDate(value: string | null): string {
	if (!value) return 'n/a';
	return new Date(value).toLocaleString();
}

export function formatCampaignPercent(value: number | null): string {
	if (value === null || Number.isNaN(value)) return 'n/a';
	return `${(value * 100).toFixed(1)}%`;
}

export function formatCampaignDelta(value: number): string {
	return `${value > 0 ? '+' : ''}${value}`;
}

export function formatCampaignRateDelta(value: number | null): string {
	if (value === null || Number.isNaN(value)) return 'n/a';
	const points = value * 100;
	return `${points > 0 ? '+' : ''}${points.toFixed(1)} pts`;
}

export function getFunnelAlertTone(status: FunnelHealthAlert['status']): string {
	if (status === 'critical') return 'border-danger-500/40 bg-danger-500/10 text-danger-200';
	if (status === 'watch') return 'border-warning-500/40 bg-warning-500/10 text-warning-200';
	if (status === 'healthy') return 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200';
	return 'border-ink-700 bg-ink-900/70 text-ink-300';
}

export function buildLandingCampaignApiPath(windowDays: number): string {
	const params = new URLSearchParams({
		days: String(windowDays),
		limit: String(QUERY_LIMIT)
	});
	return edgeApiPath(`/admin/landing/campaigns?${params.toString()}`);
}

export function extractLandingCampaignApiError(payload: unknown): string | null {
	if (!payload || typeof payload !== 'object') return null;
	const body = payload as Record<string, unknown>;
	if (typeof body.detail === 'string' && body.detail.trim()) return body.detail;
	if (typeof body.error === 'string' && body.error.trim()) return body.error;
	if (typeof body.message === 'string' && body.message.trim()) return body.message;
	return null;
}
