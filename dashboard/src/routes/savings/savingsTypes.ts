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
