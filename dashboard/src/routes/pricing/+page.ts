import { edgeApiPath } from '$lib/edgeProxy';
import { fetchWithTimeout } from '$lib/fetchWithTimeout';
import { DEFAULT_PRICING_PLANS, isPricingPlanArray } from './plans';
import type { PageLoad } from './$types';

const PRICING_REQUEST_TIMEOUT_MS = 5000;

export const load: PageLoad = async ({ fetch }) => {
	try {
		const response = await fetchWithTimeout(
			fetch,
			edgeApiPath('/billing/plans'),
			{},
			PRICING_REQUEST_TIMEOUT_MS
		);

		if (!response.ok) {
			return { plans: DEFAULT_PRICING_PLANS };
		}

		const payload = await response.json();
		if (isPricingPlanArray(payload) && payload.length > 0) {
			return { plans: payload };
		}
	} catch {
		return { plans: DEFAULT_PRICING_PLANS };
	}

	return { plans: DEFAULT_PRICING_PLANS };
};
