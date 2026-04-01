export const SUPPORTED_CURRENCIES = Object.freeze([
	{ code: 'USD', label: 'USD ($)', symbol: '$' },
	{ code: 'EUR', label: 'EUR (€)', symbol: '€' },
	{ code: 'GBP', label: 'GBP (£)', symbol: '£' },
	{ code: 'NGN', label: 'NGN (₦)', symbol: '₦' },
	{ code: 'CNY', label: 'CNY (¥)', symbol: '¥' }
]);

const CURRENCY_LOCALES: Record<string, string> = Object.freeze({
	USD: 'en-US',
	EUR: 'de-DE',
	GBP: 'en-GB',
	NGN: 'en-NG',
	CNY: 'zh-CN'
});

const DISPLAY_FX_RATES_FROM_USD: Record<string, number> = Object.freeze({
	USD: 1,
	EUR: 0.92,
	GBP: 0.79,
	NGN: 1580,
	CNY: 7.2
});

function roundCurrency(value: number): number {
	if (!Number.isFinite(value)) return 0;
	return Math.round(value * 100) / 100;
}

export function normalizeSupportedCurrencyCode(currencyCode: string | null | undefined): string {
	const normalized = String(currencyCode ?? '')
		.trim()
		.toUpperCase();
	return SUPPORTED_CURRENCIES.some((currency) => currency.code === normalized) ? normalized : 'USD';
}

export function getCurrencyMetadata(currencyCode: string | null | undefined) {
	const normalized = normalizeSupportedCurrencyCode(currencyCode);
	return (
		SUPPORTED_CURRENCIES.find((currency) => currency.code === normalized) ?? SUPPORTED_CURRENCIES[0]
	);
}

export function convertUsdAmount(amountUsd: number, currencyCode: string = 'USD'): number {
	const normalizedCurrencyCode = normalizeSupportedCurrencyCode(currencyCode);
	const fxRate = DISPLAY_FX_RATES_FROM_USD[normalizedCurrencyCode] ?? 1;
	return roundCurrency((Number.isFinite(amountUsd) ? amountUsd : 0) * fxRate);
}

export function formatCurrencyAmount(amountUsd: number, currencyCode: string = 'USD'): string {
	const normalizedCurrencyCode = normalizeSupportedCurrencyCode(currencyCode);
	const safeAmount = convertUsdAmount(amountUsd, normalizedCurrencyCode);
	const locale = CURRENCY_LOCALES[normalizedCurrencyCode] ?? 'en-US';

	try {
		return new Intl.NumberFormat(locale, {
			style: 'currency',
			currency: normalizedCurrencyCode,
			maximumFractionDigits: 0,
			minimumFractionDigits: 0
		}).format(safeAmount);
	} catch {
		return `${normalizedCurrencyCode} ${safeAmount.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
	}
}
