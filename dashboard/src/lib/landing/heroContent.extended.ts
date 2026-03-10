import { getPublicCustomerCommentsFeed } from '$lib/landing/customerCommentsFeed';
import {
	DEFAULT_PRICING_PLANS,
	getStartingPriceLabel,
	type PricingPlan
} from '$lib/pricing/publicPlans';

export const CUSTOMER_QUOTES = Object.freeze(
	getPublicCustomerCommentsFeed().map((record) => ({
		quote: record.quote,
		attribution: record.attribution
	}))
);

export const COMPLIANCE_FOUNDATION_BADGES = Object.freeze([
	'Read-only cloud onboarding where supported',
	'Encrypted connector secrets',
	'Single sign-on (SAML)',
	'SCIM user provisioning',
	'Role-based approvals',
	'Decision history export',
	'Audit log coverage',
	'Tenant isolation',
	'DPA and BAA review support',
	'Workflow approvals and routing',
	'Cloud, SaaS, and software coverage',
	'Export-ready records'
]);

type PlanCompareCard = {
	id: string;
	name: string;
	price: string;
	badge: string;
	popular: boolean;
	headline: string;
	summary: string;
	priceNote: string;
	bestFor: string;
	whyUpgrade: string;
	features: string[];
};

function toPlanCompareCard(plan: PricingPlan): PlanCompareCard {
	const story = plan.story;
	if (!story) {
		throw new Error(`Missing public plan story for plan ${plan.id}`);
	}
	return {
		id: plan.id,
		name: plan.name,
		price: getStartingPriceLabel(plan),
		badge: story.badge,
		popular: plan.popular,
		headline: story.headline,
		summary: story.summary,
		priceNote: `$${plan.price_monthly}/mo starting price. ${story.note}`,
		bestFor: story.bestFor,
		whyUpgrade: story.whyUpgrade,
		features: [...plan.features]
	};
}

export const PLAN_COMPARE_CARDS = Object.freeze(
	DEFAULT_PRICING_PLANS.filter((plan) => plan.id !== 'free').map((plan) => toPlanCompareCard(plan))
);

export const PLANS_PRICING_EXPLANATION =
	'Monthly starting prices shown here are entry points. Start self-serve for a first controlled workflow, then use the enterprise path when governance depth, procurement, or finance close requirements expand.';

export const FREE_TIER_HIGHLIGHTS = Object.freeze([
	'Permanent free workspace for one owner-routed savings workflow',
	'1 AWS account with core dashboards and alerts',
	'Weekly zombie scans plus 30-day history',
	'1 guided AI analysis per day with BYOK support'
]);

export const FREE_TIER_LIMIT_NOTE =
	'Free is best for proving one controlled workflow with no procurement overhead. Upgrade when you need broader provider coverage, team rollout, or finance-grade governance.';

export const IMPLEMENTATION_COST_FACTS = Object.freeze([
	'Typical rollout: 3-10 business days for the first controlled production workflow.',
	'Common team footprint: one engineering owner plus one finance or FinOps owner.',
	'Read-only onboarding is available where supported for initial cloud access.',
	'Rollout assumptions stay visible up front in pricing, planning, and proof materials.'
]);

export const CROSS_SURFACE_COVERAGE = Object.freeze([
	{
		title: 'Catch waste before close',
		detail:
			'Spot cloud and software cost movement earlier and route it before month-end pressure turns it into escalation.'
	},
	{
		title: 'Give every issue an owner',
		detail:
			'Every material anomaly lands with a named owner, a decision path, and a deadline instead of another thread.'
	},
	{
		title: 'Review one shared control loop',
		detail:
			'Cloud, SaaS, license, and carbon decisions stay in one operating narrative leadership can review quickly.'
	}
]);

export const DECISION_LEDGER_SUMMARY = Object.freeze([
	{ label: 'Scope', value: 'Cloud + SaaS + software' },
	{ label: 'Action path', value: 'Owner, policy, workflow' },
	{ label: 'Proof', value: 'Decision log + export' }
]);

export const DECISION_LEDGER_STEPS = Object.freeze([
	{
		step: '01',
		kicker: 'Signal scoped',
		title: 'The issue lands with owner, scope, and financial context',
		detail:
			'Valdrics ties spend movement to the affected workload, team, service, and decision path instead of leaving another chart for someone to interpret.',
		meta: 'Service mapped. Owner queue opened.'
	},
	{
		step: '02',
		kicker: 'Guardrails applied',
		title: 'Policy, budget, and approval checks stay attached',
		detail:
			'Risk checks, role boundaries, workflow routing, and approval paths stay attached before action moves forward, so teams do not trade speed for control.',
		meta: 'Pre-change checks passed. Approval path visible.'
	},
	{
		step: '03',
		kicker: 'Action and proof recorded',
		title: 'Leadership gets a reviewable action trail and savings proof',
		detail:
			'Every finished action keeps its rationale, owner, approvals, and savings proof so finance, engineering, and security can review one clean record.',
		meta: 'Decision saved. Export-ready record available.'
	}
]);

export const BACKEND_CAPABILITY_PILLARS = Object.freeze([
	{
		title: 'Cost Intelligence and Forecasting',
		detail:
			'Track spend, attribution, anomalies, and forecast movement before variance turns into escalation.'
	},
	{
		title: 'GreenOps Execution',
		detail:
			'Manage carbon budgets, regional intensity, and greener workload scheduling in the same workflow as cost.'
	},
	{
		title: 'Cloud Hygiene and Remediation',
		detail:
			'Detect idle resources, route owner actions, and execute approved remediation with built-in safety checks.'
	},
	{
		title: 'SaaS and ITAM License Control',
		detail:
			'Bring SaaS usage and license posture into one view so reclamation and renewal decisions stay measurable.'
	},
	{
		title: 'Financial Guardrails',
		detail:
			'Apply budgets, credits, reservations, and approval flows so high-impact spend actions stay controlled.'
	},
	{
		title: 'Savings Proof for Leadership',
		detail:
			'Show realized savings events, leaderboard movement, and executive-ready operating outcomes.'
	},
	{
		title: 'Operational Integrations',
		detail:
			'Connect Slack, Teams, Jira, and workflow alerts so decisions move into the channels teams already use.'
	},
	{
		title: 'Security and Identity',
		detail:
			'Support SSO, SCIM provisioning, role-scoped approvals, and audit-ready decision history.'
	}
]);
