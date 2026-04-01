import { json } from '@sveltejs/kit';
import {
	resolveCountryCodeFromHeaders,
	resolveGeoCurrencyFromHeaders
} from '$lib/landing/geoCurrency';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ request }) => {
	const countryCode = resolveCountryCodeFromHeaders(request.headers);
	const currencyCode = resolveGeoCurrencyFromHeaders(request.headers);
	const source = countryCode ? 'ip_country_header' : 'default';

	return json(
		{
			currencyCode,
			countryCode,
			source
		},
		{
			headers: {
				'cache-control': 'private, max-age=300, stale-while-revalidate=900'
			}
		}
	);
};
