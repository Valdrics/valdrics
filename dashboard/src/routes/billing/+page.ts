import { edgeApiPath } from '$lib/edgeProxy';
import { fetchWithTimeout } from '$lib/fetchWithTimeout';
import type { PageLoad } from './$types';
import { isBillingUsagePayload } from './billingPage';
import { DEFAULT_PRICING_PLANS, isPricingPlanArray } from '../pricing/plans';

const BILLING_REQUEST_TIMEOUT_MS = 5000;

async function readJson(response: Response): Promise<unknown> {
	try {
		return await response.json();
	} catch {
		return null;
	}
}

export const load: PageLoad = async ({ fetch, parent, url }) => {
	const parentData = await parent();
	const checkoutSuccess = url.searchParams.get('success') === 'true';
	const accessToken = parentData.session?.access_token;

	if (!accessToken) {
		return {
			plans: DEFAULT_PRICING_PLANS,
			usage: null,
			checkoutSuccess
		};
	}

	const headers = {
		Authorization: `Bearer ${accessToken}`
	};

	const [plansResponse, usageResponse] = await Promise.all([
		fetchWithTimeout(fetch, edgeApiPath('/billing/plans'), {}, BILLING_REQUEST_TIMEOUT_MS).catch(
			() => null
		),
		fetchWithTimeout(
			fetch,
			edgeApiPath('/billing/usage'),
			{ headers },
			BILLING_REQUEST_TIMEOUT_MS
		).catch(() => null)
	]);

	let plans = DEFAULT_PRICING_PLANS;
	if (plansResponse) {
		const payload = await readJson(plansResponse);
		if (isPricingPlanArray(payload) && payload.length > 0) {
			plans = payload;
		}
	}

	let usage = null;
	if (usageResponse?.ok) {
		const payload = await readJson(usageResponse);
		if (isBillingUsagePayload(payload)) {
			usage = payload;
		}
	}

	return {
		plans,
		usage,
		checkoutSuccess
	};
};
