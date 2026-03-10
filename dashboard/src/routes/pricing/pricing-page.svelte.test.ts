import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import Page from './+page.svelte';
import { DEFAULT_PRICING_PLANS } from './plans';

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

vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

vi.mock('$app/stores', () => {
	return {
		page: readable({
			url: new URL('https://example.com/pricing')
		})
	};
});

describe('pricing page public messaging', () => {
	it('shows the free tier entry path plus self-serve paid plans and enterprise lane', () => {
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
					plans: DEFAULT_PRICING_PLANS
				}
			}
		});

		expect(
			screen.getByRole('heading', { level: 1, name: /simple, transparent pricing/i })
		).toBeTruthy();
		expect(screen.getByText(/^Start on the permanent free tier,/i)).toBeTruthy();
		expect(
			screen.getByRole('heading', { name: /^free tier for your first savings workflow$/i })
		).toBeTruthy();
		expect(
			screen.getByRole('link', { name: /start on free tier/i }).getAttribute('href')
		).toContain('/auth/login?mode=signup&plan=free');
		expect(screen.getByRole('heading', { name: /^starter$/i })).toBeTruthy();
		expect(screen.getByRole('heading', { name: /^growth$/i })).toBeTruthy();
		expect(screen.getByRole('heading', { name: /^pro$/i })).toBeTruthy();
		expect(
			screen.getAllByText(/one governed savings workflow|one governed workflow/i).length
		).toBeGreaterThan(0);
		expect(screen.getAllByText(/^Best for$/i).length).toBeGreaterThanOrEqual(4);
		expect(screen.getAllByText(/^Why teams upgrade$/i).length).toBeGreaterThanOrEqual(4);
		expect(
			screen.getByText(
				/one team needs daily review cadence, initial azure\/gcp visibility, and stronger owner routing/i
			)
		).toBeTruthy();
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
		expect(screen.getByText(growthPlan?.story?.whyUpgrade ?? '')).toBeTruthy();
		const growthPlanCard = screen.getByRole('heading', { name: /^growth$/i }).closest('article');
		expect(growthPlanCard?.className).toContain('pricing-plan-card--popular');

		expect(
			screen.getByRole('heading', {
				name: /use the enterprise lane only when security or procurement needs a separate track/i
			})
		).toBeTruthy();
		expect(
			screen.getByText(
				/bring in sales when scim, private deployment, procurement, or custom control requirements/i
			)
		).toBeTruthy();
		expect(screen.getByText(/prices are shown in usd for easy plan comparison/i)).toBeTruthy();
		expect(
			screen.getByText(/the permanent free tier does not require a checkout session/i)
		).toBeTruthy();

		const salesCta = screen.getAllByRole('link', { name: /talk to sales/i });
		expect(salesCta.length).toBeGreaterThan(0);
		expect(
			screen.getByRole('link', { name: /view enterprise overview/i }).getAttribute('href')
		).toBe('/enterprise');
	});
});
