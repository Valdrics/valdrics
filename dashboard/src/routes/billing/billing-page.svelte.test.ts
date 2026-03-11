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
		const starterPlan = DEFAULT_PRICING_PLANS.find((plan) => plan.id === 'starter');
		const growthPlan = DEFAULT_PRICING_PLANS.find((plan) => plan.id === 'growth');
		const proPlan = DEFAULT_PRICING_PLANS.find((plan) => plan.id === 'pro');

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
			(document.body.textContent || '').includes(
				`$49/mo starting price. ${starterPlan?.story?.note}`
			)
		).toBe(true);
		expect(
			(document.body.textContent || '').includes(
				`$149/mo starting price. ${growthPlan?.story?.note}`
			)
		).toBe(true);
		expect(
			(document.body.textContent || '').includes(`$299/mo starting price. ${proPlan?.story?.note}`)
		).toBe(true);
		expect(screen.getAllByText(/^Best for$/i).length).toBeGreaterThanOrEqual(4);
		expect(screen.getAllByText(/^Why teams upgrade$/i).length).toBeGreaterThanOrEqual(4);
		expect(
			screen.getByText(
				/cross-functional teams need full aws, azure, and gcp coverage with owner routing/i
			)
		).toBeTruthy();
		expect(
			screen.getByText(
				/move to the enterprise lane only when scim, private deployment, procurement review/i
			)
		).toBeTruthy();
		const growthPlanCard = screen.getByRole('heading', { name: /^growth$/i }).closest('article');
		expect(growthPlanCard?.className).toContain('billing-plan-card--popular');
	});
});
