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

	it('persists an explicit supported currency selection', async () => {
		const module = await loadModuleWithDetectedCurrency('EUR');
		module.setLandingCurrencyPreference('GBP');

		expect(window.localStorage.getItem('valdrics_landing_currency')).toBe('GBP');
		expect(module.getLandingCurrencyPreference()).toBe('GBP');
		expect(module.resolveInitialLandingCurrency()).toBe('GBP');
	});

	it('falls back to the detected local currency when storage contains an unsupported value', async () => {
		window.localStorage.setItem('valdrics_landing_currency', 'INVALID');

		const module = await loadModuleWithDetectedCurrency('CNY');
		expect(module.getLandingCurrencyPreference()).toBe('CNY');
		expect(module.resolveInitialLandingCurrency()).toBe('CNY');
	});

	it('ignores unsupported currency values and preserves the prior valid preference', async () => {
		const module = await loadModuleWithDetectedCurrency('NGN');
		module.setLandingCurrencyPreference('EUR');
		module.setLandingCurrencyPreference('ZZZ' as 'USD');

		expect(module.getLandingCurrencyPreference()).toBe('EUR');
		expect(window.localStorage.getItem('valdrics_landing_currency')).toBe('EUR');
	});
});
