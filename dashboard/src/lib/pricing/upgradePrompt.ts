import { DEFAULT_PRICING_PLANS, type PricingPlan } from '$lib/pricing/publicPlans';

type SupportedUpgradePlanId = 'starter' | 'growth' | 'pro';

export type UpgradePrompt = {
	badge: string;
	heading: string;
	body: string;
	footnote: string;
	cta: string;
};

const PLAN_BY_ID = new Map(
	DEFAULT_PRICING_PLANS.map((plan) => [plan.id, plan] as const)
);

function getRequiredPlan(planId: SupportedUpgradePlanId): PricingPlan {
	const plan = PLAN_BY_ID.get(planId);
	if (!plan) {
		throw new Error(`Missing pricing plan for upgrade prompt: ${planId}`);
	}
	return plan;
}

export function getUpgradePrompt(
	planId: SupportedUpgradePlanId,
	capabilityLabel: string
): UpgradePrompt {
	const plan = getRequiredPlan(planId);
	const planName = plan.name;

	return {
		badge: `${planName} Plan Required`,
		heading: `Move to ${planName} for ${capabilityLabel}`,
		body: plan.story?.summary ?? plan.story?.bestFor ?? plan.description,
		footnote: plan.story?.whyUpgrade ?? '',
		cta: `View ${planName} plan`
	};
}
