import { browser } from '$app/environment';
import { detectLocalCurrency, SUPPORTED_CURRENCIES } from '$lib/landing/roiCalculator';

export type LandingCurrencyCode = 'USD' | 'EUR' | 'GBP' | 'NGN' | 'CNY';

const STORAGE_KEY = 'valdrics_landing_currency';
const SUPPORTED_CODES = new Set(
	SUPPORTED_CURRENCIES.map((currency) => currency.code as LandingCurrencyCode)
);

function normalizeCurrencyCode(value: unknown): LandingCurrencyCode | null {
	const normalized = String(value ?? '')
		.trim()
		.toUpperCase();
	if (!SUPPORTED_CODES.has(normalized as LandingCurrencyCode)) {
		return null;
	}
	return normalized as LandingCurrencyCode;
}

export function getLandingCurrencyPreference(): LandingCurrencyCode {
	if (!browser) return 'USD';
	try {
		return (
			normalizeCurrencyCode(window.localStorage.getItem(STORAGE_KEY)) ??
			resolveDetectedLandingCurrency()
		);
	} catch {
		return resolveDetectedLandingCurrency();
	}
}

export function setLandingCurrencyPreference(code: LandingCurrencyCode): void {
	if (!browser) return;
	const normalized = normalizeCurrencyCode(code);
	if (!normalized) return;
	try {
		window.localStorage.setItem(STORAGE_KEY, normalized);
	} catch {
		// Best-effort preference persistence.
	}
}

export function resolveInitialLandingCurrency(): LandingCurrencyCode {
	return getLandingCurrencyPreference();
}

export function resolveDetectedLandingCurrency(): LandingCurrencyCode {
	if (!browser) return 'USD';
	return normalizeCurrencyCode(detectLocalCurrency()) ?? 'USD';
}
