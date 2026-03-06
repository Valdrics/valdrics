export type PendingRequest = {
	id: string;
	status: string;
	resource_id: string;
	resource_type: string;
	action: string;
	provider?: string;
	region?: string;
	connection_id?: string | null;
	estimated_savings: number;
	scheduled_execution_at?: string | null;
	escalation_required?: boolean;
	escalation_reason?: string | null;
	escalated_at?: string | null;
	created_at: string | null;
};

export type PolicyPreview = {
	decision: string;
	summary: string;
	tier: string;
	rule_hits: Array<{ rule_id: string; message: string }>;
};

export type JobStatus = {
	pending: number;
	running: number;
	completed: number;
	failed: number;
	dead_letter: number;
};

export type JobSLOMetric = {
	job_type: string;
	window_hours: number;
	target_success_rate_percent: number;
	total_jobs: number;
	successful_jobs: number;
	failed_jobs: number;
	success_rate_percent: number;
	meets_slo: boolean;
	latest_completed_at?: string | null;
	avg_duration_seconds?: number | null;
	p95_duration_seconds?: number | null;
};

export type JobSLOResponse = {
	window_hours: number;
	target_success_rate_percent: number;
	overall_meets_slo: boolean;
	metrics: JobSLOMetric[];
};

export type JobRecord = {
	id: string;
	job_type: string;
	status: string;
	attempts: number;
	created_at: string;
	error_message?: string;
};

export type StrategyRecommendation = {
	id: string;
	resource_type: string;
	region: string;
	term: string;
	payment_option: string;
	estimated_monthly_savings: number;
	roi_percentage: number;
	status: string;
};

export type UnitEconomicsMetric = {
	metric_key: string;
	label: string;
	denominator: number;
	total_cost: number;
	cost_per_unit: number;
	baseline_cost_per_unit: number;
	delta_percent: number;
	is_anomalous: boolean;
};

export type UnitEconomicsResponse = {
	start_date: string;
	end_date: string;
	total_cost: number;
	baseline_total_cost: number;
	threshold_percent: number;
	anomaly_count: number;
	alert_dispatched: boolean;
	metrics: UnitEconomicsMetric[];
};

export type UnitEconomicsSettings = {
	id: string;
	default_request_volume: number;
	default_workload_volume: number;
	default_customer_volume: number;
	anomaly_threshold_percent: number;
};

export type IngestionSLAResponse = {
	window_hours: number;
	target_success_rate_percent: number;
	total_jobs: number;
	successful_jobs: number;
	failed_jobs: number;
	success_rate_percent: number;
	meets_sla: boolean;
	latest_completed_at: string | null;
	avg_duration_seconds: number | null;
	p95_duration_seconds: number | null;
	records_ingested: number;
};

export type AcceptanceKpiMetric = {
	key: string;
	label: string;
	available: boolean;
	target: string;
	actual: string;
	meets_target: boolean;
	details: Record<string, unknown>;
};

export type AcceptanceKpisResponse = {
	start_date: string;
	end_date: string;
	tier: string;
	all_targets_met: boolean;
	available_metrics: number;
	metrics: AcceptanceKpiMetric[];
};

export type AcceptanceKpiEvidenceItem = {
	event_id: string;
	run_id: string | null;
	captured_at: string;
	actor_id: string | null;
	actor_email: string | null;
	success: boolean;
	acceptance_kpis: AcceptanceKpisResponse;
};

export type AcceptanceKpiEvidenceResponse = {
	total: number;
	items: AcceptanceKpiEvidenceItem[];
};

export type AcceptanceKpiCaptureResponse = {
	status: string;
	event_id: string;
	run_id: string;
	captured_at: string;
	acceptance_kpis: AcceptanceKpisResponse;
};

export type IntegrationAcceptanceEvidenceItem = {
	event_id: string;
	run_id: string | null;
	event_type: string;
	channel: string;
	success: boolean;
	status_code: number | null;
	message: string | null;
	actor_email: string | null;
	event_timestamp: string;
	details: Record<string, unknown>;
};

export type IntegrationAcceptanceEvidenceResponse = {
	total: number;
	items: IntegrationAcceptanceEvidenceItem[];
};

export type IntegrationAcceptanceCaptureResponse = {
	run_id: string;
	tenant_id: string;
	captured_at: string;
	overall_status: string;
	passed: number;
	failed: number;
	results: Array<{
		channel: string;
		success: boolean;
		status_code: number;
		message: string;
	}>;
};

export type IntegrationAcceptanceRunChannel = {
	channel: string;
	success: boolean;
	statusCode: number | null;
	message: string | null;
	eventTimestamp: string;
};

export type IntegrationAcceptanceRun = {
	runId: string;
	capturedAt: string;
	overallStatus: string;
	passed: number;
	failed: number;
	checkedChannels: string[];
	actorEmail: string | null;
	channels: IntegrationAcceptanceRunChannel[];
};

export type ReconciliationClosePackage = {
	tenant_id: string;
	provider: string | null;
	period: { start_date: string; end_date: string };
	close_status: string;
	lifecycle: {
		total_records: number;
		preliminary_records: number;
		final_records: number;
		total_cost_usd: number;
		preliminary_cost_usd: number;
		final_cost_usd: number;
	};
	reconciliation: {
		status: string;
		discrepancy_percentage: number;
		confidence?: number;
		comparison_basis?: string;
	};
	restatements: {
		count: number;
		net_delta_usd: number;
		absolute_delta_usd: number;
	};
	invoice_reconciliation?: {
		status: string;
		provider: string;
		period: { start_date: string; end_date: string };
		threshold_percent: number;
		invoice?: {
			id: string;
			invoice_number?: string | null;
			currency: string;
			total_amount: number;
			total_amount_usd: number;
			status: string;
			notes?: string | null;
			updated_at?: string | null;
		};
		ledger_final_cost_usd?: number;
		delta_usd?: number;
		absolute_delta_usd?: number;
		delta_percent?: number;
	} | null;
	integrity_hash: string;
	package_version: string;
};

export type ProviderInvoiceForm = {
	invoice_number: string;
	currency: string;
	total_amount: number;
	status: string;
	notes: string;
};
