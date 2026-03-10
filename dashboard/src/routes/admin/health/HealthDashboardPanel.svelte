<script lang="ts">
	import { Activity, Cloud, RefreshCw, Server, Wallet } from '@lucide/svelte';

	import type { FairUseRuntime, HealthDashboard } from './healthTypes';

	let {
		dashboard,
		fairUse,
		fairUseError,
		refreshing = false,
		onRefresh
	}: {
		dashboard: HealthDashboard;
		fairUse: FairUseRuntime | null;
		fairUseError: string;
		refreshing?: boolean;
		onRefresh: () => Promise<void> | void;
	} = $props();

	function formatDate(value: string): string {
		return new Date(value).toLocaleString();
	}

	function formatUsd(value: number): string {
		return new Intl.NumberFormat('en-US', {
			style: 'currency',
			currency: 'USD',
			maximumFractionDigits: 2
		}).format(value || 0);
	}

	function formatMs(value: number): string {
		return `${Math.round(value || 0).toLocaleString()} ms`;
	}

	function formatLimit(value: number | null | undefined): string {
		if (!value || value <= 0) return 'disabled';
		return value.toLocaleString();
	}

	function formatPercent(value: number | null | undefined): string {
		if (value === null || value === undefined || Number.isNaN(value)) return 'n/a';
		return `${(value * 100).toFixed(1)}%`;
	}

	function formatRateDelta(value: number | null | undefined): string {
		if (value === null || value === undefined || Number.isNaN(value)) return 'n/a';
		const points = value * 100;
		return `${points > 0 ? '+' : ''}${points.toFixed(1)} pts`;
	}

	function statusBadgeClass(status: string | undefined): string {
		switch ((status || '').toLowerCase()) {
			case 'healthy':
				return 'badge badge-success';
			case 'degraded':
				return 'badge badge-warning';
			case 'critical':
				return 'badge badge-error';
			default:
				return 'badge badge-default';
		}
	}
</script>

<div class="space-y-8 page-enter">
	<div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
		<div>
			<h1 class="text-2xl font-bold mb-1">Internal Health Dashboard</h1>
			<p class="text-ink-400 text-sm">Operational metrics pulled from live governance telemetry for internal operators.</p>
		</div>
		<div class="flex items-center gap-2">
			<span class={statusBadgeClass(dashboard.system.status)}>{dashboard.system.status.toUpperCase()}</span>
			<button type="button" class="btn btn-secondary text-xs" onclick={onRefresh} disabled={refreshing}>
				<RefreshCw class="h-3.5 w-3.5" />
				{refreshing ? 'Refreshing...' : 'Refresh'}
			</button>
		</div>
	</div>

	<div class="text-xs text-ink-500">
		Generated: {formatDate(dashboard.generated_at)} | Last check:
		{formatDate(dashboard.system.last_check)}
	</div>

	<div class="grid gap-5 md:grid-cols-2 lg:grid-cols-5">
		<div class="card card-stat">
			<div class="flex items-center justify-between mb-2">
				<p class="text-xs text-ink-400 uppercase tracking-wide">System Uptime</p>
				<Activity class="h-4 w-4 text-ink-400" />
			</div>
			<p class="text-3xl font-bold">{dashboard.system.uptime_hours.toLocaleString()}h</p>
		</div>
		<div class="card card-stat">
			<div class="flex items-center justify-between mb-2">
				<p class="text-xs text-ink-400 uppercase tracking-wide">Jobs Running</p>
				<Server class="h-4 w-4 text-ink-400" />
			</div>
			<p class="text-3xl font-bold text-accent-400">{dashboard.job_queue.running_jobs}</p>
			<p class="text-xs text-danger-400 mt-1">{dashboard.job_queue.failed_last_24h} failed in last 24h</p>
		</div>
		<div class="card card-stat">
			<div class="flex items-center justify-between mb-2">
				<p class="text-xs text-ink-400 uppercase tracking-wide">LLM Cost (24h)</p>
				<Wallet class="h-4 w-4 text-ink-400" />
			</div>
			<p class="text-3xl font-bold text-warning-400">{formatUsd(dashboard.llm_usage.estimated_cost_24h)}</p>
			<p class="text-xs text-ink-500 mt-1">{dashboard.llm_usage.total_requests_24h.toLocaleString()} requests</p>
		</div>
		<div class="card card-stat">
			<div class="flex items-center justify-between mb-2">
				<p class="text-xs text-ink-400 uppercase tracking-wide">Cloud Connections</p>
				<Cloud class="h-4 w-4 text-ink-400" />
			</div>
			<p class="text-3xl font-bold text-success-400">
				{dashboard.cloud_connections.active_connections}/{dashboard.cloud_connections.total_connections}
			</p>
			<p class="text-xs text-ink-500 mt-1">
				AWS {dashboard.cloud_connections.providers?.aws?.active_connections ?? 0}/
				{dashboard.cloud_connections.providers?.aws?.total_connections ?? 0} | Azure
				{dashboard.cloud_connections.providers?.azure?.active_connections ?? 0}/
				{dashboard.cloud_connections.providers?.azure?.total_connections ?? 0} | GCP
				{dashboard.cloud_connections.providers?.gcp?.active_connections ?? 0}/
				{dashboard.cloud_connections.providers?.gcp?.total_connections ?? 0}
			</p>
		</div>
		<div class="card card-stat">
			<div class="flex items-center justify-between mb-2">
				<p class="text-xs text-ink-400 uppercase tracking-wide">Cloud+ Connections</p>
				<Cloud class="h-4 w-4 text-ink-400" />
			</div>
			<p class="text-3xl font-bold text-accent-400">
				{dashboard.cloud_plus_connections.active_connections}/{dashboard.cloud_plus_connections
					.total_connections}
			</p>
			<p class="text-xs text-ink-500 mt-1">{dashboard.cloud_plus_connections.errored_connections} errored</p>
		</div>
	</div>

	<div class="grid gap-5 lg:grid-cols-2">
		<div class="card space-y-4">
			<h2 class="text-lg font-semibold">Tenant Activity</h2>
			<div class="grid grid-cols-2 gap-3 text-sm">
				<div class="frosted-glass rounded-lg p-3">
					<p class="text-ink-400 text-xs uppercase">Total</p>
					<p class="text-xl font-bold">{dashboard.tenants.total_tenants}</p>
				</div>
				<div class="frosted-glass rounded-lg p-3">
					<p class="text-ink-400 text-xs uppercase">Paid</p>
					<p class="text-xl font-bold text-success-400">{dashboard.tenants.paid_tenants}</p>
				</div>
				<div class="frosted-glass rounded-lg p-3">
					<p class="text-ink-400 text-xs uppercase">Active 24h</p>
					<p class="text-xl font-bold">{dashboard.tenants.active_last_24h}</p>
				</div>
				<div class="frosted-glass rounded-lg p-3">
					<p class="text-ink-400 text-xs uppercase">Churn Risk</p>
					<p class="text-xl font-bold text-warning-400">{dashboard.tenants.churn_risk}</p>
				</div>
			</div>
		</div>

		<div class="card space-y-4">
			<h2 class="text-lg font-semibold">Job Queue Latency</h2>
			<div class="space-y-2 text-sm">
				<div class="flex items-center justify-between">
					<span class="text-ink-400">Pending jobs</span>
					<span>{dashboard.job_queue.pending_jobs}</span>
				</div>
				<div class="flex items-center justify-between">
					<span class="text-ink-400">Dead-letter queue</span>
					<span>{dashboard.job_queue.dead_letter_count}</span>
				</div>
				<div class="flex items-center justify-between">
					<span class="text-ink-400">Average</span>
					<span>{formatMs(dashboard.job_queue.avg_processing_time_ms)}</span>
				</div>
				<div class="flex items-center justify-between">
					<span class="text-ink-400">P50</span>
					<span>{formatMs(dashboard.job_queue.p50_processing_time_ms)}</span>
				</div>
				<div class="flex items-center justify-between">
					<span class="text-ink-400">P95</span>
					<span>{formatMs(dashboard.job_queue.p95_processing_time_ms)}</span>
				</div>
				<div class="flex items-center justify-between">
					<span class="text-ink-400">P99</span>
					<span>{formatMs(dashboard.job_queue.p99_processing_time_ms)}</span>
				</div>
			</div>
		</div>
	</div>

	<div class="card space-y-4">
		<h2 class="text-lg font-semibold">License Governance (24h)</h2>
		<div class="grid grid-cols-2 gap-3 text-sm">
			<div class="frosted-glass rounded-lg p-3">
				<p class="text-ink-400 text-xs uppercase">Active Connections</p>
				<p class="text-xl font-bold">{dashboard.license_governance.active_license_connections}</p>
			</div>
			<div class="frosted-glass rounded-lg p-3">
				<p class="text-ink-400 text-xs uppercase">Requests Created</p>
				<p class="text-xl font-bold">{dashboard.license_governance.requests_created_24h}</p>
			</div>
			<div class="frosted-glass rounded-lg p-3">
				<p class="text-ink-400 text-xs uppercase">Completed</p>
				<p class="text-xl font-bold text-success-400">{dashboard.license_governance.requests_completed_24h}</p>
			</div>
			<div class="frosted-glass rounded-lg p-3">
				<p class="text-ink-400 text-xs uppercase">Failed</p>
				<p class="text-xl font-bold text-danger-400">{dashboard.license_governance.requests_failed_24h}</p>
			</div>
		</div>
		<div class="space-y-2 text-sm">
			<div class="flex items-center justify-between">
				<span class="text-ink-400">Completion rate</span>
				<span>{dashboard.license_governance.completion_rate_percent.toFixed(2)}%</span>
			</div>
			<div class="flex items-center justify-between">
				<span class="text-ink-400">Failure rate</span>
				<span>{dashboard.license_governance.failure_rate_percent.toFixed(2)}%</span>
			</div>
			<div class="flex items-center justify-between">
				<span class="text-ink-400">In-flight requests</span>
				<span>{dashboard.license_governance.requests_in_flight}</span>
			</div>
			<div class="flex items-center justify-between">
				<span class="text-ink-400">Avg completion time</span>
				<span>
					{dashboard.license_governance.avg_time_to_complete_hours === null
						? 'n/a'
						: `${dashboard.license_governance.avg_time_to_complete_hours.toFixed(2)}h`}
				</span>
			</div>
		</div>
	</div>

	<div class="card">
		<h2 class="text-lg font-semibold mb-3">LLM Budget Position</h2>
		<div class="space-y-2 text-sm">
			<div class="flex items-center justify-between">
				<span class="text-ink-400">Budget utilization</span>
				<span>{dashboard.llm_usage.budget_utilization.toFixed(2)}%</span>
			</div>
			<div class="w-full bg-ink-800 rounded-full h-2 overflow-hidden">
				<div
					class="h-full transition-all duration-500"
					class:bg-success-500={dashboard.llm_usage.budget_utilization < 70}
					class:bg-warning-500={dashboard.llm_usage.budget_utilization >= 70 &&
						dashboard.llm_usage.budget_utilization < 90}
					class:bg-danger-500={dashboard.llm_usage.budget_utilization >= 90}
					style="width: {Math.min(dashboard.llm_usage.budget_utilization, 100)}%"
				></div>
			</div>
			<div class="flex items-center justify-between">
				<span class="text-ink-400">Cache hit rate</span>
				<span>{(dashboard.llm_usage.cache_hit_rate * 100).toFixed(1)}%</span>
			</div>
		</div>
	</div>

	<div class="card">
		<h2 class="text-lg font-semibold mb-3">Landing Funnel Health</h2>
		<div class="grid gap-4 lg:grid-cols-4">
			<div class="frosted-glass rounded-lg p-3">
				<p class="text-ink-400 text-xs uppercase">7d signup → connection</p>
				<p class="text-xl font-bold">{formatPercent(dashboard.landing_funnel.weekly_current.signup_to_connection_rate)}</p>
				<p class="text-xs text-ink-500 mt-1">
					{formatRateDelta(dashboard.landing_funnel.weekly_delta.signup_to_connection_rate)}
				</p>
			</div>
			<div class="frosted-glass rounded-lg p-3">
				<p class="text-ink-400 text-xs uppercase">7d connection → first value</p>
				<p class="text-xl font-bold">
					{formatPercent(dashboard.landing_funnel.weekly_current.connection_to_first_value_rate)}
				</p>
				<p class="text-xs text-ink-500 mt-1">
					{formatRateDelta(dashboard.landing_funnel.weekly_delta.connection_to_first_value_rate)}
				</p>
			</div>
			<div class="frosted-glass rounded-lg p-3">
				<p class="text-ink-400 text-xs uppercase">7d PQL</p>
				<p class="text-xl font-bold">{dashboard.landing_funnel.weekly_current.pql_tenants}</p>
				<p class="text-xs text-ink-500 mt-1">
					Δ {dashboard.landing_funnel.weekly_delta.pql_tenants > 0 ? '+' : ''}{dashboard.landing_funnel.weekly_delta.pql_tenants}
				</p>
			</div>
			<div class="frosted-glass rounded-lg p-3">
				<p class="text-ink-400 text-xs uppercase">7d paid activations</p>
				<p class="text-xl font-bold">{dashboard.landing_funnel.weekly_current.paid_tenants}</p>
				<p class="text-xs text-ink-500 mt-1">
					Δ {dashboard.landing_funnel.weekly_delta.paid_tenants > 0 ? '+' : ''}{dashboard.landing_funnel.weekly_delta.paid_tenants}
				</p>
			</div>
		</div>
		<div class="grid gap-3 mt-4 lg:grid-cols-2">
			{#each dashboard.landing_funnel.alerts as alert (alert.key)}
				<div class="frosted-glass rounded-lg p-3">
					<div class="flex items-start justify-between gap-3">
						<div>
							<p class="text-ink-400 text-xs uppercase">{alert.label}</p>
							<p class="text-lg font-bold mt-1">{formatPercent(alert.current_rate)}</p>
						</div>
						<span class={statusBadgeClass(alert.status)}>{alert.status.toUpperCase()}</span>
					</div>
					<p class="text-sm text-ink-300 mt-3">{alert.message}</p>
					<p class="text-xs text-ink-500 mt-2">
						Floor {formatPercent(alert.threshold_rate)} · Previous {formatPercent(alert.previous_rate)} · Delta {formatRateDelta(alert.weekly_delta)}
					</p>
					<p class="text-xs text-ink-500 mt-1">
						{alert.current_numerator}/{alert.current_denominator} tenants in the current week
					</p>
				</div>
			{/each}
		</div>
	</div>

	<div class="card">
		<h2 class="text-lg font-semibold mb-3">LLM Fair-Use Runtime</h2>
		{#if fairUse}
			<div class="space-y-2 text-sm">
				<div class="flex items-center justify-between">
					<span class="text-ink-400">Guardrails</span>
					<span class={statusBadgeClass(fairUse.guards_enabled ? 'healthy' : 'degraded')}>
						{fairUse.guards_enabled ? 'ON' : 'OFF'}
					</span>
				</div>
				<div class="flex items-center justify-between">
					<span class="text-ink-400">Tenant tier</span>
					<span>{fairUse.tenant_tier.toUpperCase()}</span>
				</div>
				<div class="flex items-center justify-between">
					<span class="text-ink-400">Enforced for this tenant</span>
					<span class={statusBadgeClass(fairUse.active_for_tenant ? 'healthy' : 'degraded')}>
						{fairUse.active_for_tenant ? 'YES' : 'NO'}
					</span>
				</div>
				<div class="pt-2 border-t border-ink-800">
					<p class="text-ink-500 text-xs uppercase mb-2 tracking-wide">Thresholds</p>
					<div class="space-y-2">
						<div class="flex items-center justify-between">
							<span class="text-ink-400">Pro daily soft cap</span>
							<span>{formatLimit(fairUse.thresholds.pro_daily_soft_cap)}</span>
						</div>
						<div class="flex items-center justify-between">
							<span class="text-ink-400">Enterprise daily soft cap</span>
							<span>{formatLimit(fairUse.thresholds.enterprise_daily_soft_cap)}</span>
						</div>
						<div class="flex items-center justify-between">
							<span class="text-ink-400">Per-minute cap</span>
							<span>{formatLimit(fairUse.thresholds.per_minute_cap)}</span>
						</div>
						<div class="flex items-center justify-between">
							<span class="text-ink-400">Per-tenant concurrency cap</span>
							<span>{formatLimit(fairUse.thresholds.per_tenant_concurrency_cap)}</span>
						</div>
						<div class="flex items-center justify-between">
							<span class="text-ink-400">Concurrency lease TTL</span>
							<span>{fairUse.thresholds.concurrency_lease_ttl_seconds}s</span>
						</div>
					</div>
				</div>
			</div>
		{:else if fairUseError}
			<p class="text-danger-400 text-sm">{fairUseError}</p>
		{:else}
			<p class="text-ink-400 text-sm">Fair-use runtime status is not available.</p>
		{/if}
	</div>
</div>
