import { describe, expect, it } from 'vitest';

import {
	SPEND_PROVIDER_OPTIONS,
	normalizeSpendProvider,
	operationalProviderParam,
	spendProviderParam
} from './spendProviderFilters';

describe('spend provider filters', () => {
	it('exposes AI in the canonical spend provider options', () => {
		expect(SPEND_PROVIDER_OPTIONS).toContainEqual({ id: 'ai', name: 'AI' });
		expect(spendProviderParam(' AI ')).toBe('ai');
	});

	it('does not send AI to operational provider filters', () => {
		expect(operationalProviderParam('ai')).toBeUndefined();
		expect(operationalProviderParam('aws')).toBe('aws');
	});

	it('drops unsupported query-string providers before API requests', () => {
		expect(normalizeSpendProvider('not-a-provider')).toBe('');
		expect(spendProviderParam('not-a-provider')).toBeUndefined();
	});
});
