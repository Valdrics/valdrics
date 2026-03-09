import { edgeApiPath } from '$lib/edgeProxy';

export const GREENOPS_DEFAULT_PROVIDER = 'aws';
export const GREENOPS_DEFAULT_REGION = 'us-east-1';

type CarbonWindow = {
	startDate: string;
	endDate: string;
	region?: string;
	provider?: string;
};

export function buildCarbonFootprintPath({
	startDate,
	endDate,
	region = GREENOPS_DEFAULT_REGION,
	provider = GREENOPS_DEFAULT_PROVIDER
}: CarbonWindow): string {
	const params = new URLSearchParams({
		start_date: startDate,
		end_date: endDate,
		region,
		provider
	});
	return edgeApiPath(`/carbon?${params.toString()}`);
}

export function buildCarbonBudgetPath({
	region = GREENOPS_DEFAULT_REGION,
	provider = GREENOPS_DEFAULT_PROVIDER
}: Omit<CarbonWindow, 'startDate' | 'endDate'>): string {
	const params = new URLSearchParams({
		region,
		provider
	});
	return edgeApiPath(`/carbon/budget?${params.toString()}`);
}

export function buildCarbonIntensityPath(region: string, hours: number): string {
	const params = new URLSearchParams({
		region,
		hours: String(hours)
	});
	return edgeApiPath(`/carbon/intensity?${params.toString()}`);
}

export function buildGreenSchedulePath(region: string, durationHours: number): string {
	const params = new URLSearchParams({
		region,
		duration_hours: String(durationHours)
	});
	return edgeApiPath(`/carbon/schedule?${params.toString()}`);
}

export function buildGravitonPath(region: string): string {
	const params = new URLSearchParams({
		region
	});
	return edgeApiPath(`/carbon/graviton?${params.toString()}`);
}
