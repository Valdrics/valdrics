import { resolvePublicLandingCurrencyFromHeaders } from '$lib/landing/geoCurrency';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ request }) => ({
	detectedCurrencyCode: resolvePublicLandingCurrencyFromHeaders(request.headers)
});
