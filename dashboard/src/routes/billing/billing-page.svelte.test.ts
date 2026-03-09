import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';

import Page from './+page.svelte';
import { DEFAULT_PRICING_PLANS } from '../pricing/plans';

vi.mock('$env/dynamic/public', () => ({
	env: {
		PUBLIC_API_URL: 'https://api.test/api/v1'
	}
}));

vi.mock('$env/static/public', () => ({
	PUBLIC_API_URL: 'https://api.test/api/v1'
}));

vi.mock('$app/paths', () => ({
	assets: '',
	base: ''
}));

describe('billing page plan messaging', () => {
	it('reuses the shared plan value narrative from pricing', () => {
		render(Page, {
			props: {
				data: {
					user: null,
					session: null,
					subscription: { tier: 'free', status: 'active' },
					profile: null,
					plans: DEFAULT_PRICING_PLANS,
					usage: null,
					checkoutSuccess: false
				}
			}
		});

		expect(screen.getByRole('heading', { level: 1, name: /subscription and usage/i })).toBeTruthy();
		expect(
			screen.getByText(/\$49\/mo starting price\. priced for the first team that needs daily review cadence/i)
		).toBeTruthy();
		expect(
			screen.getByText(/\$149\/mo starting price\. priced for the first cross-functional rollout/i)
		).toBeTruthy();
		expect(
			screen.getByText(/\$299\/mo starting price\. priced for finance-grade operations/i)
		).toBeTruthy();
		expect(screen.getAllByText(/^Best for$/i).length).toBeGreaterThanOrEqual(4);
		expect(screen.getAllByText(/^Why teams upgrade$/i).length).toBeGreaterThanOrEqual(4);
		expect(
			screen.getByText(/cross-functional teams need full aws, azure, and gcp coverage with owner routing/i)
		).toBeTruthy();
		expect(
			screen.getByText(/move to the enterprise lane only when scim, private deployment, procurement review/i)
		).toBeTruthy();
	});
});
