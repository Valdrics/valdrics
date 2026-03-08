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
};

export const DEFAULT_PRICING_PLANS: PricingPlan[] = [
	{
		id: 'free',
		name: 'Free',
		price_monthly: 0,
		price_annual: 0,
		period: '/mo',
		description: 'Permanent free tier for proving one owner-routed savings workflow.',
		features: [
			'One owner-routed savings workflow',
			'Cloud and software signal map access',
			'Baseline owner routing and approval workflow',
			'BYOK supported; daily AI limits still apply by tier'
		],
		cta: 'Start on Free Tier',
		popular: false
	},
	{
		id: 'starter',
		name: 'Starter',
		price_monthly: 49,
		price_annual: 490,
		period: '/mo',
		description: 'For focused teams running one provider scope with clearer owner routing.',
		features: [
			'Includes all Free features',
			'Multi-account support',
			'Advanced budget alerts',
			'90-day data retention'
		],
		cta: 'Start with Starter',
		popular: false
	},
	{
		id: 'growth',
		name: 'Growth',
		price_monthly: 149,
		price_annual: 1490,
		period: '/mo',
		description: 'For multi-cloud teams that need approvals, guided execution, and broader coverage.',
		features: [
			'Includes all Starter features',
			'AWS + Azure + GCP support',
			'Approval workflows + GreenOps',
			'Non-production auto-remediation'
		],
		cta: 'Start with Growth',
		popular: true
	},
	{
		id: 'pro',
		name: 'Pro',
		price_monthly: 299,
		price_annual: 2990,
		period: '/mo',
		description: 'For teams that want deeper automation, API access, and stronger governance evidence.',
		features: [
			'Includes all Growth features',
			'Expanded automation and API access',
			'Compliance exports and audit evidence',
			'Priority support'
		],
		cta: 'Start with Pro',
		popular: false
	}
];
