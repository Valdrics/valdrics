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
		description:
			'Permanent free tier for proving one live savings workflow before broader rollout.',
		features: [
			'1 AWS account with core dashboards and alerts',
			'Weekly zombie scans and 30-day retention',
			'1 guided AI analysis per day',
			'Permanent workspace; upgrade only when coverage expands'
		],
		cta: 'Start Free Workspace',
		popular: false,
		story: {
			badge: 'Self-serve proof lane',
			headline: 'Free tier for your first savings workflow',
			summary:
				'Start at $0, prove one controlled savings workflow, and upgrade only when you need broader coverage, stronger owner routing, or deeper governance controls.',
			note: 'Free is best for proving one controlled workflow before you expand into broader provider coverage, faster review cadence, or expanded governance support.',
			bestFor:
				'Proving one owner-routed savings workflow with one AWS account and no procurement friction.',
			whyUpgrade:
				'Upgrade when you need broader provider coverage, faster review cadence, team rollout controls, or finance-grade governance.'
		}
	},
	{
		id: 'starter',
		name: 'Starter',
		price_monthly: 49,
		price_annual: 490,
		period: '/mo',
		description:
			'For small teams that need daily review cadence and limited cross-cloud visibility.',
		features: [
			'Includes all Free features',
			'Up to 5 AWS accounts plus 1 Azure tenant and 1 GCP project',
			'AI insights, stronger alerting, and ingestion SLA monitoring',
			'90-day data retention'
		],
		cta: 'Start Starter Workspace',
		popular: false,
		story: {
			badge: 'Focused operator lane',
			headline: 'Daily review cadence with limited cross-cloud visibility',
			summary:
				'Best for the first team that needs daily review cadence, initial cross-cloud visibility, and clearer owner routing without moving into a formal enterprise buying path too early.',
			note: 'Priced for the first team that needs daily review cadence, initial cross-cloud visibility, and stronger owner routing without paying for broader governance too early.',
			bestFor:
				'One team needs daily review cadence, initial Azure/GCP visibility, and stronger owner routing before a broader rollout.',
			whyUpgrade:
				'Teams usually move up when full multi-cloud execution, Slack and Jira collaboration, or SSO become operational requirements.'
		}
	},
	{
		id: 'growth',
		name: 'Growth',
		price_monthly: 149,
		price_annual: 1490,
		period: '/mo',
		description:
			'For multi-cloud teams that need owner routing, SSO rollout, and guided execution.',
		features: [
			'Includes all Starter features',
			'Full AWS + Azure + GCP coverage with anomaly detection',
			'Slack, Jira, and SSO for team rollout',
			'Chargeback, backfill, and non-production auto-remediation'
		],
		cta: 'Start Growth Workspace',
		popular: true,
		story: {
			badge: 'Recommended paid plan',
			headline: 'Multi-cloud execution with identity and team rollout attached',
			summary:
				'Best for cross-functional teams that need full multi-cloud coverage, owner routing, Slack, Jira, SSO rollout, and guided execution across functions before a finance-grade rollout is required.',
			note: 'Priced for the first cross-functional team that needs full multi-cloud coverage, owner routing, Slack, Jira, and SSO to land together.',
			bestFor:
				'Cross-functional teams need full AWS, Azure, and GCP coverage with owner routing, Slack, Jira, and SSO rollout.',
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
		description:
			'For teams that need finance-grade controls, APIs, and exportable governance evidence.',
		features: [
			'Includes all Growth features',
			'API access, audit logs, and hourly scans',
			'Reconciliation, close workflow, and compliance exports',
			'Cloud+ connectors, savings proof, and incident integrations'
		],
		cta: 'Start Pro Workspace',
		popular: false,
		story: {
			badge: 'Automation lane',
			headline: 'Finance-grade governance, APIs, and proof',
			summary:
				'Best for teams that need finance-grade operations: auditability, finance close support, cloud-plus connectors, workflow automation, and stronger evidence for leadership, security, and audit review while staying self-serve.',
			note: 'Priced for finance-grade self-serve rollout once auditability, API access, reconciliation, workflow automation, and export-ready evidence become operational requirements.',
			bestFor:
				'Finance, platform, and leadership need APIs, audit logs, reconciliation, close workflow, workflow automation, and stronger governance evidence.',
			whyUpgrade:
				'Move to the enterprise lane only when SCIM, private deployment, procurement review, or custom control requirements need a separate buying path.'
		}
	}
];
