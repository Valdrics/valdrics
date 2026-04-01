import { browser } from '$app/environment';
import { detectLocalCurrency } from '$lib/landing/roiCalculator';
import {
	normalizeLandingCurrencyCode,
	type LandingCurrencyCode
} from '$lib/landing/landingCurrencyPolicy';

export type { LandingCurrencyCode } from '$lib/landing/landingCurrencyPolicy';

const STORAGE_KEY = 'valdrics_landing_currency';

export function getLandingCurrencyPreference(
	fallback: LandingCurrencyCode = resolveDetectedLandingCurrency()
): LandingCurrencyCode {
	if (!browser) return fallback;
	try {
		const storedCurrency = normalizeLandingCurrencyCode(window.localStorage.getItem(STORAGE_KEY));
		if (!storedCurrency) {
			return fallback;
		}
		return storedCurrency === 'USD' || storedCurrency === fallback ? storedCurrency : fallback;
	} catch {
		return fallback;
	}
}

export function setLandingCurrencyPreference(code: LandingCurrencyCode): void {
	if (!browser) return;
	const normalized = normalizeLandingCurrencyCode(code);
	if (!normalized) return;
	try {
		window.localStorage.setItem(STORAGE_KEY, normalized);
	} catch {
		// Best-effort preference persistence.
	}
}

export function resolveInitialLandingCurrency(
	fallback: LandingCurrencyCode = resolveDetectedLandingCurrency()
): LandingCurrencyCode {
	return getLandingCurrencyPreference(fallback);
}

export function resolveDetectedLandingCurrency(): LandingCurrencyCode {
	if (!browser) return 'USD';
	return normalizeLandingCurrencyCode(detectLocalCurrency()) ?? 'USD';
}
