export type PricingPlanStory = {
	badge: string;
	headline: string;
	summary: string;
	note: string;
	bestFor: string;
	whyUpgrade: string;
};

export type PricingPlan = {
	id: string;
	name: string;
	price_monthly: number;
	price_annual: number;
	period: string;
	description: string;
	features: string[];
	cta: string;
	popular: boolean;
	feature_maturity?: Record<string, string>;
	story?: PricingPlanStory;
};

export const PLAN_ORDER = ['free', 'starter', 'growth', 'pro'] as const;

export function isPricingPlan(value: unknown): value is PricingPlan {
	if (typeof value !== 'object' || value === null) return false;
	const plan = value as Partial<PricingPlan>;
	return (
		typeof plan.id === 'string' &&
		typeof plan.name === 'string' &&
		typeof plan.price_monthly === 'number' &&
		typeof plan.price_annual === 'number' &&
		typeof plan.period === 'string' &&
		typeof plan.description === 'string' &&
		Array.isArray(plan.features) &&
		plan.features.every((feature) => typeof feature === 'string') &&
		typeof plan.cta === 'string' &&
		typeof plan.popular === 'boolean'
	);
}

export function isPricingPlanArray(value: unknown): value is PricingPlan[] {
	return Array.isArray(value) && value.every((item) => isPricingPlan(item));
}

export function mergePricingPlans(incomingPlans: PricingPlan[]): PricingPlan[] {
	const byId = new Map(DEFAULT_PRICING_PLANS.map((plan) => [plan.id, plan] as const));
	for (const plan of incomingPlans) {
		const existing = byId.get(plan.id);
		byId.set(plan.id, existing ? { ...existing, ...plan, story: existing.story } : plan);
	}

	const knownPlans = PLAN_ORDER.map((planId) => byId.get(planId)).filter(
		(plan): plan is PricingPlan => Boolean(plan)
	);
	const extras = incomingPlans.filter(
		(plan) => !PLAN_ORDER.includes(plan.id as (typeof PLAN_ORDER)[number])
	);
	return [...knownPlans, ...extras];
}

export function getStartingPriceLabel(plan: PricingPlan): string {
	return plan.price_monthly === 0 ? '$0' : `From $${plan.price_monthly}/mo`;
}

export const DEFAULT_PRICING_PLANS: PricingPlan[] = [
	{
		id: 'free',
		name: 'Free',
		price_monthly: 0,
		price_annual: 0,
		period: '/mo',
		description: 'Permanent free tier for proving one live savings workflow before broader rollout.',
		features: [
			'1 AWS account with core dashboards and alerts',
			'Weekly zombie scans and 30-day retention',
			'1 guided AI analysis per day',
			'Permanent workspace; upgrade only when coverage expands'
		],
		cta: 'Start on Free Tier',
		popular: false,
		story: {
			badge: 'Start here first',
			headline: 'Free tier for your first savings workflow',
			summary:
				'Start at $0, prove one workflow, and upgrade only when you need more coverage, automation, or governance depth.',
			note:
				'Free is best for proving one workflow before you expand into multi-cloud coverage, deeper automation, or expanded governance support.',
			bestFor:
				'Proving one live savings workflow with one AWS account and no checkout friction.',
			whyUpgrade:
				'Upgrade when you need broader provider coverage, more frequent analysis, or team rollout controls.'
		}
	},
	{
		id: 'starter',
		name: 'Starter',
		price_monthly: 49,
		price_annual: 490,
		period: '/mo',
		description: 'For small teams that need daily review cadence and limited cross-cloud visibility.',
		features: [
			'Includes all Free features',
			'Up to 5 AWS accounts plus 1 Azure tenant and 1 GCP project',
			'AI insights, stronger alerting, and ingestion SLA monitoring',
			'90-day data retention'
		],
		cta: 'Start with Starter',
		popular: false,
		story: {
			badge: 'Focused operator lane',
			headline: 'Daily review cadence with limited cross-cloud visibility',
			summary:
				'Best for a smaller operating scope when one team needs clearer owner routing, stronger alerts, and limited Azure/GCP visibility without jumping straight to a broader governance plan.',
			note: 'Best fit for a compact cross-cloud operating scope with one core review team.',
			bestFor:
				'One team needs daily review cadence, limited Azure/GCP visibility, and stronger alerting before a broader rollout.',
			whyUpgrade:
				'Teams usually move up when owner routing, full multi-cloud coverage, Slack workflows, or SSO become operational requirements.'
		}
	},
	{
		id: 'growth',
		name: 'Growth',
		price_monthly: 149,
		price_annual: 1490,
		period: '/mo',
		description: 'For multi-cloud teams that need owner routing, SSO rollout, and guided execution.',
		features: [
			'Includes all Starter features',
			'Full AWS + Azure + GCP coverage with anomaly detection',
			'Slack-integrated workflows and SSO',
			'Chargeback, backfill, and non-production auto-remediation'
		],
		cta: 'Start with Growth',
		popular: true,
		story: {
			badge: 'Most popular',
			headline: 'Multi-cloud execution with identity and team rollout attached',
			summary:
				'Best for teams that need broader provider coverage, owner routing, Slack-integrated workflows, SSO rollout, and guided execution across functions.',
			note:
				'Built for broader provider coverage, team rollout, and stronger cross-functional governance.',
			bestFor:
				'Cross-functional teams need full AWS, Azure, and GCP coverage with owner routing, Slack workflows, and SSO rollout.',
			whyUpgrade:
				'Teams usually move up when finance close, auditability, Cloud+ connectors, or export-ready governance evidence become required.'
		}
	},
	{
		id: 'pro',
		name: 'Pro',
		price_monthly: 299,
		price_annual: 2990,
		period: '/mo',
		description: 'For teams that need finance-grade controls, APIs, and exportable governance evidence.',
		features: [
			'Includes all Growth features',
			'API access, audit logs, and hourly scans',
			'Reconciliation, close workflow, and compliance exports',
			'Cloud+ connectors, savings proof, and incident integrations'
		],
		cta: 'Start with Pro',
		popular: false,
		story: {
			badge: 'Automation lane',
			headline: 'Finance-grade governance, APIs, and proof',
			summary:
				'Best for teams that want higher automation depth, finance close support, cloud-plus connectors, and stronger evidence for leadership, security, and audit review.',
			note: 'Adds APIs, finance workflow support, and stronger governance evidence.',
			bestFor:
				'Finance, platform, and leadership need APIs, audit logs, reconciliation, close workflow, and stronger governance evidence.',
			whyUpgrade:
				'Move to the enterprise lane only when SCIM, private deployment, procurement review, or custom control requirements need a separate buying path.'
		}
	}
];
