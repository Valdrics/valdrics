export type HealthDashboard = {
	generated_at: string;
	system: {
		status: string;
		uptime_hours: number;
		last_check: string;
	};
	tenants: {
		total_tenants: number;
		active_last_24h: number;
		active_last_7d: number;
		free_tenants: number;
		paid_tenants: number;
		churn_risk: number;
	};
	job_queue: {
		pending_jobs: number;
		running_jobs: number;
		failed_last_24h: number;
		dead_letter_count: number;
		avg_processing_time_ms: number;
		p50_processing_time_ms: number;
		p95_processing_time_ms: number;
		p99_processing_time_ms: number;
	};
	llm_usage: {
		total_requests_24h: number;
		cache_hit_rate: number;
		estimated_cost_24h: number;
		budget_utilization: number;
	};
	cloud_connections: {
		total_connections: number;
		active_connections: number;
		inactive_connections: number;
		errored_connections: number;
		providers: Record<
			string,
			{
				total_connections: number;
				active_connections: number;
				inactive_connections: number;
				errored_connections: number;
			}
		>;
	};
	cloud_plus_connections: {
		total_connections: number;
		active_connections: number;
		inactive_connections: number;
		errored_connections: number;
		providers: Record<
			string,
			{
				total_connections: number;
				active_connections: number;
				inactive_connections: number;
				errored_connections: number;
			}
		>;
	};
	license_governance: {
		window_hours: number;
		active_license_connections: number;
		requests_created_24h: number;
		requests_completed_24h: number;
		requests_failed_24h: number;
		requests_in_flight: number;
		completion_rate_percent: number;
		failure_rate_percent: number;
		avg_time_to_complete_hours: number | null;
	};
};

export type FairUseRuntime = {
	generated_at: string;
	guards_enabled: boolean;
	tenant_tier: string;
	tier_eligible: boolean;
	active_for_tenant: boolean;
	thresholds: {
		pro_daily_soft_cap: number | null;
		enterprise_daily_soft_cap: number | null;
		per_minute_cap: number | null;
		per_tenant_concurrency_cap: number | null;
		concurrency_lease_ttl_seconds: number;
		enforced_tiers: string[];
	};
};
