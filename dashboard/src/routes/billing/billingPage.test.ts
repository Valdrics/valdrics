import { describe, expect, it } from 'vitest';

import { canSelfServeCheckout, getVisibleBillingPlans } from './billingPage';
import { DEFAULT_PRICING_PLANS } from '../pricing/plans';

describe('billing page plan rules', () => {
	it('hides downgrade paths for self-serve tiers', () => {
		const visible = getVisibleBillingPlans(DEFAULT_PRICING_PLANS, 'starter');

		expect(visible.map((plan) => plan.id)).toEqual(['starter', 'growth', 'pro']);
	});

	it('keeps all self-serve plans visible for enterprise workspaces', () => {
		const visible = getVisibleBillingPlans(DEFAULT_PRICING_PLANS, 'enterprise');

		expect(visible.map((plan) => plan.id)).toEqual(['free', 'starter', 'growth', 'pro']);
	});

	it('allows checkout only for higher paid plans', () => {
		expect(canSelfServeCheckout('free', 'free')).toBe(false);
		expect(canSelfServeCheckout('starter', 'free')).toBe(true);
		expect(canSelfServeCheckout('growth', 'starter')).toBe(true);
		expect(canSelfServeCheckout('starter', 'growth')).toBe(false);
	});
});
