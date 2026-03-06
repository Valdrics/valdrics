export type CarbonData = {
	total_co2_kg: number;
	scope2_co2_kg: number;
	scope3_co2_kg: number;
	carbon_efficiency_score: number;
	estimated_energy_kwh: number;
	forecast_30d?: { projected_co2_kg: number };
	equivalencies?: {
		miles_driven: number;
		trees_needed_for_year: number;
		smartphone_charges: number;
		percent_of_home_month: number;
	};
	green_region_recommendations?: Array<{
		region: string;
		carbon_intensity: number;
		savings_percent: number;
	}>;
};

export type GravitonData = {
	candidates?: Array<{
		instance_id: string;
		energy_savings_percent: number;
		current_type: string;
		recommended_type: string;
	}>;
};

export type BudgetData = {
	alert_status: 'ok' | 'warning' | 'exceeded' | string;
	current_usage_kg: number;
	budget_kg: number;
	usage_percent: number;
};

export type IntensityData = {
	source?: string;
	forecast?: Array<{
		hour_utc: string;
		intensity_gco2_kwh: number;
		level: 'very_low' | 'low' | 'medium' | 'high' | 'very_high' | string;
	}>;
};

export type ScheduleResult = {
	optimal_start_time: string | null;
	recommendation: string;
};
