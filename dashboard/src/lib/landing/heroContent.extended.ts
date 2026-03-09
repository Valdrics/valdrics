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
	'ISO 27001 readiness alignment',
	'DORA operational resilience',
	'SOC 2 program alignment',
	'GDPR data-rights support',
	'Single sign-on (SAML)',
	'SCIM user provisioning',
	'Role-based approvals',
	'Decision history logs',
	'DPA and BAA review support',
	'Export-ready records',
	'Tenant isolation'
]);

type PlanCompareCard = {
	id: string;
	name: string;
	price: string;
	badge: string;
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
		headline: story.headline,
		summary: story.summary,
		priceNote: `Monthly starting price. ${story.note}`,
		bestFor: story.bestFor,
		whyUpgrade: story.whyUpgrade,
		features: [...plan.features]
	};
}

export const PLAN_COMPARE_CARDS = Object.freeze(
	DEFAULT_PRICING_PLANS.filter((plan) => plan.id !== 'free').map((plan) => toPlanCompareCard(plan))
);

export const PLANS_PRICING_EXPLANATION =
	'Monthly starting prices shown here are entry points. Upgrade as provider coverage, workflow automation depth, and governance needs expand.';

export const FREE_TIER_HIGHLIGHTS = Object.freeze([
	'Permanent free workspace for one live savings workflow',
	'1 AWS account with core dashboards and alerts',
	'Weekly zombie scans plus 30-day history',
	'1 guided AI analysis per day with BYOK support'
]);

export const FREE_TIER_LIMIT_NOTE =
	'Free is best for proving one workflow permanently. Upgrade when you need more provider coverage, team rollout controls, or finance-grade governance.';

export const IMPLEMENTATION_COST_FACTS = Object.freeze([
	'Typical rollout: 3-10 business days for first production workflow.',
	'Common team footprint: one engineering owner + one finance/FinOps owner.',
	'No mandatory professional-services retainer for core onboarding.',
	'Implementation effort is visible upfront in the ROI planner assumptions.'
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
	{ label: 'Scope', value: 'Cloud + software + carbon' },
	{ label: 'Control loop', value: 'Owner, approval, proof' },
	{ label: 'Review rhythm', value: 'Weekly finance + engineering' }
]);

export const DECISION_LEDGER_STEPS = Object.freeze([
	{
		step: '01',
		kicker: 'Signal scoped',
		title: 'The issue lands with owner and context',
		detail:
			'Valdrics ties spend movement to the affected workload, team, and decision path instead of leaving another chart for someone to interpret.',
		meta: 'Workload tagged. Owner queue opened.'
	},
	{
		step: '02',
		kicker: 'Guardrails applied',
		title: 'Approval happens with the right checks',
		detail:
			'Risk checks, role boundaries, and approval routes stay attached before action moves forward, so teams do not trade speed for control.',
		meta: 'Pre-change checks passed. Approval path visible.'
	},
	{
		step: '03',
		kicker: 'Outcome recorded',
		title: 'Leadership gets a reviewable decision trail',
		detail:
			'Every finished action keeps its rationale, owner, and savings proof so finance, engineering, and security can review one clean record.',
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
