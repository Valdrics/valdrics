import { detectCurrencyFromCountryCode } from '$lib/landing/roiCalculator';
import { resolveLandingCurrencyCode, type LandingCurrencyCode } from './landingCurrencyPolicy';

export function normalizeCountryCode(value: string | null): string | null {
	if (!value) return null;
	const normalized = value.trim().toUpperCase();
	if (!normalized || normalized === 'XX') return null;
	return normalized;
}

export function resolveCountryCodeFromHeaders(headers: Headers): string | null {
	return (
		normalizeCountryCode(headers.get('cf-ipcountry')) ||
		normalizeCountryCode(headers.get('x-vercel-ip-country')) ||
		null
	);
}

export function resolveGeoCurrencyFromHeaders(headers: Headers): string {
	const countryCode = resolveCountryCodeFromHeaders(headers);
	return detectCurrencyFromCountryCode(countryCode) ?? 'USD';
}

export function resolvePublicLandingCurrencyFromHeaders(headers: Headers): LandingCurrencyCode {
	return resolveLandingCurrencyCode(resolveGeoCurrencyFromHeaders(headers));
}
