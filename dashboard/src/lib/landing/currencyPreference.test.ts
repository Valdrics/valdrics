// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest';

describe('currencyPreference', () => {
	async function loadModuleWithDetectedCurrency(detectedCurrency: string) {
		vi.doMock('$app/environment', () => ({ browser: true }));
		vi.doMock('$lib/landing/roiCalculator', () => ({
			detectLocalCurrency: () => detectedCurrency,
			SUPPORTED_CURRENCIES: [
				{ code: 'USD', label: 'USD ($)', symbol: '$' },
				{ code: 'EUR', label: 'EUR (€)', symbol: '€' },
				{ code: 'GBP', label: 'GBP (£)', symbol: '£' },
				{ code: 'NGN', label: 'NGN (₦)', symbol: '₦' },
				{ code: 'CNY', label: 'CNY (¥)', symbol: '¥' }
			]
		}));

		return import('./currencyPreference');
	}

	afterEach(() => {
		window.localStorage.clear();
		vi.resetModules();
		vi.clearAllMocks();
	});

	it('defaults to the detected local currency when no explicit preference exists', async () => {
		const module = await loadModuleWithDetectedCurrency('EUR');
		expect(module.getLandingCurrencyPreference()).toBe('EUR');
		expect(module.resolveInitialLandingCurrency()).toBe('EUR');
		expect(module.resolveDetectedLandingCurrency()).toBe('EUR');
	});

	it('persists an explicit USD selection across visits', async () => {
		const module = await loadModuleWithDetectedCurrency('EUR');
		module.setLandingCurrencyPreference('USD');

		expect(window.localStorage.getItem('valdrics_landing_currency')).toBe('USD');
		expect(module.getLandingCurrencyPreference()).toBe('USD');
		expect(module.resolveInitialLandingCurrency()).toBe('USD');
	});

	it('falls back to the detected local currency when storage contains an unsupported value', async () => {
		window.localStorage.setItem('valdrics_landing_currency', 'INVALID');

		const module = await loadModuleWithDetectedCurrency('CNY');
		expect(module.getLandingCurrencyPreference()).toBe('CNY');
		expect(module.resolveInitialLandingCurrency()).toBe('CNY');
	});

	it('ignores unsupported currency values and preserves the current valid public preference', async () => {
		const module = await loadModuleWithDetectedCurrency('EUR');
		module.setLandingCurrencyPreference('USD');
		module.setLandingCurrencyPreference('NGN' as 'USD');
		module.setLandingCurrencyPreference('ZZZ' as 'USD');

		expect(module.getLandingCurrencyPreference()).toBe('USD');
		expect(window.localStorage.getItem('valdrics_landing_currency')).toBe('USD');
	});

	it('falls back to USD when the detected local currency is NGN', async () => {
		const module = await loadModuleWithDetectedCurrency('NGN');

		expect(module.resolveDetectedLandingCurrency()).toBe('USD');
		expect(module.resolveInitialLandingCurrency()).toBe('USD');
	});

	it('ignores a previously stored NGN landing preference', async () => {
		window.localStorage.setItem('valdrics_landing_currency', 'NGN');

		const module = await loadModuleWithDetectedCurrency('EUR');
		expect(module.getLandingCurrencyPreference()).toBe('EUR');
		expect(module.resolveInitialLandingCurrency()).toBe('EUR');
	});

	it('ignores a stale stored local currency when the current detected local currency changes', async () => {
		window.localStorage.setItem('valdrics_landing_currency', 'GBP');

		const module = await loadModuleWithDetectedCurrency('EUR');
		expect(module.getLandingCurrencyPreference()).toBe('EUR');
		expect(module.resolveInitialLandingCurrency()).toBe('EUR');
	});
});
