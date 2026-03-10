import type { PricingPlan } from '../pricing/plans';
import { PLAN_ORDER, mergePricingPlans } from '../pricing/plans';

export type BillingCycle = 'monthly' | 'annual';
export type BillingSubscription = {
	tier?: string;
	status?: string;
	next_payment_date?: string | null;
};

export type ConnectionUsageItem = {
	connected: number;
	limit: number | null;
	remaining: number | null;
	utilization_percent: number | null;
};

export type BillingUsage = {
	tier: string;
	connections: Record<string, ConnectionUsageItem>;
	generated_at: string;
};

export const BILLING_USAGE_ORDER = ['aws', 'azure', 'gcp', 'saas', 'license'] as const;

export const BILLING_USAGE_LABELS: Record<(typeof BILLING_USAGE_ORDER)[number], string> = {
	aws: 'AWS accounts',
	azure: 'Azure tenants',
	gcp: 'GCP projects',
	saas: 'SaaS connections',
	license: 'License connections'
};

const PLAN_RANK = new Map<string, number>([
	...PLAN_ORDER.map((planId, index) => [planId, index] as const),
	['enterprise', PLAN_ORDER.length]
]);

export function isBillingUsagePayload(value: unknown): value is BillingUsage {
	if (typeof value !== 'object' || value === null) return false;
	const payload = value as Partial<BillingUsage>;
	return (
		typeof payload.tier === 'string' &&
		typeof payload.generated_at === 'string' &&
		typeof payload.connections === 'object' &&
		payload.connections !== null
	);
}

export function getPlanRank(planId: string): number {
	return PLAN_RANK.get(String(planId).trim().toLowerCase()) ?? -1;
}

export function mergeBillingPlans(plans: PricingPlan[]): PricingPlan[] {
	return mergePricingPlans(plans);
}

export function getVisibleBillingPlans(plans: PricingPlan[], currentTier: string): PricingPlan[] {
	const currentRank = getPlanRank(currentTier);
	if (currentTier === 'enterprise' || currentRank < 0) {
		return plans;
	}

	return plans.filter((plan) => {
		const planRank = getPlanRank(plan.id);
		return planRank >= currentRank;
	});
}

export function canSelfServeCheckout(planId: string, currentTier: string): boolean {
	if (planId === 'free') return false;
	return getPlanRank(planId) > getPlanRank(currentTier);
}

export function formatBillingUsd(value: number): string {
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency: 'USD',
		maximumFractionDigits: 0
	}).format(value);
}

export function formatBillingDate(timestamp: string): string {
	return new Intl.DateTimeFormat('en-US', {
		dateStyle: 'medium',
		timeStyle: 'short'
	}).format(new Date(timestamp));
}

export function getDisplayedMonthlyPlanPrice(
	plan: PricingPlan,
	billingCycle: BillingCycle
): number {
	return billingCycle === 'monthly' ? plan.price_monthly : Math.round(plan.price_annual / 12);
}

export function getAnnualPlanSavings(plan: PricingPlan): number {
	return Math.max(plan.price_monthly * 12 - plan.price_annual, 0);
}
