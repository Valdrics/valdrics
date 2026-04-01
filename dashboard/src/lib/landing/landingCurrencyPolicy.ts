export const PUBLIC_LANDING_CURRENCIES = ['USD', 'EUR', 'GBP', 'CNY'] as const;

export type LandingCurrencyCode = (typeof PUBLIC_LANDING_CURRENCIES)[number];

const PUBLIC_LANDING_CURRENCY_SET = new Set<string>(PUBLIC_LANDING_CURRENCIES);

export function normalizeLandingCurrencyCode(value: unknown): LandingCurrencyCode | null {
	const normalized = String(value ?? '')
		.trim()
		.toUpperCase();
	if (!PUBLIC_LANDING_CURRENCY_SET.has(normalized)) {
		return null;
	}
	return normalized as LandingCurrencyCode;
}

export function resolveLandingCurrencyCode(value: unknown): LandingCurrencyCode {
	return normalizeLandingCurrencyCode(value) ?? 'USD';
}
