export type SavingsProofBreakdownItem = {
	provider: string;
	opportunity_monthly_usd: number;
	realized_monthly_usd: number;
	open_recommendations: number;
	applied_recommendations: number;
	pending_remediations: number;
	completed_remediations: number;
};

export type SavingsProofResponse = {
	start_date: string;
	end_date: string;
	as_of: string;
	tier: string;
	opportunity_monthly_usd: number;
	realized_monthly_usd: number;
	open_recommendations: number;
	applied_recommendations: number;
	pending_remediations: number;
	completed_remediations: number;
	breakdown: SavingsProofBreakdownItem[];
	notes: string[];
};

export type SavingsProofDrilldownBucket = {
	key: string;
	opportunity_monthly_usd: number;
	realized_monthly_usd: number;
	open_recommendations: number;
	applied_recommendations: number;
	pending_remediations: number;
	completed_remediations: number;
};

export type SavingsProofDrilldownResponse = {
	start_date: string;
	end_date: string;
	as_of: string;
	tier: string;
	provider: string | null;
	dimension: string;
	opportunity_monthly_usd: number;
	realized_monthly_usd: number;
	buckets: SavingsProofDrilldownBucket[];
	truncated: boolean;
	limit: number;
	notes: string[];
};

export type RealizedSavingsEvent = {
	remediation_request_id: string;
	finding_id: string | null;
	finding_category: string | null;
	provider: string;
	account_id: string | null;
	resource_id: string | null;
	region: string | null;
	method: string;
	executed_at: string | null;
	baseline_start_date: string;
	baseline_end_date: string;
	measurement_start_date: string;
	measurement_end_date: string;
	baseline_avg_daily_cost_usd: number;
	measurement_avg_daily_cost_usd: number;
	realized_monthly_savings_usd: number;
	confidence_score: number | null;
	computed_at: string;
};
