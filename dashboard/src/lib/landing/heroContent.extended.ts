import { getPublicCustomerCommentsFeed } from '$lib/landing/customerCommentsFeed';

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

export const PLAN_COMPARE_CARDS = Object.freeze([
	{
		id: 'starter',
		name: 'Starter',
		price: 'From $49/mo',
		kicker: 'For focused cloud teams',
		detail: 'Move from static dashboards to owner-routed spend control in one workspace.',
		features: ['Single-cloud start', 'Budgets + anomaly routing', 'Owner action workflows']
	},
	{
		id: 'growth',
		name: 'Growth',
		price: 'From $149/mo',
		kicker: 'For cross-functional FinOps',
		detail: 'Unify cloud, SaaS, and operational ownership with guided execution loops.',
		features: ['Multi-cloud + Cloud+ signals', 'Approval workflows', 'AI-assisted prioritization']
	},
	{
		id: 'pro',
		name: 'Pro',
		price: 'From $299/mo',
		kicker: 'For enterprise teams',
		detail:
			'Scale shared execution across engineering, finance, and leadership with API-first operations.',
		features: ['Automated remediation tracks', 'Expanded API access', 'Priority support']
	}
]);

export const FREE_TIER_HIGHLIGHTS = Object.freeze([
	'Permanent free tier with usage limits',
	'Cloud and software signal map access',
	'Owner routing and baseline action workflows',
	'BYOK available with tier limits'
]);

export const IMPLEMENTATION_COST_FACTS = Object.freeze([
	'Typical rollout: 3-10 business days for first production workflow.',
	'Common team footprint: one engineering owner + one finance/FinOps owner.',
	'No mandatory professional-services retainer for core onboarding.',
	'Implementation effort is visible upfront in the ROI planner assumptions.'
]);

export const CROSS_SURFACE_COVERAGE = Object.freeze([
	{
		title: 'Cloud Infrastructure',
		detail:
			'AWS, Azure, and GCP spend signals are attributed to accountable teams before they become month-end surprises.'
	},
	{
		title: 'GreenOps and Carbon',
		detail:
			'Carbon intensity, budget thresholds, and cleaner-runtime opportunities are tracked alongside cost decisions.'
	},
	{
		title: 'SaaS Spend',
		detail:
			'Vendor usage and expansion pressure are surfaced with ownership context so renewals become controlled decisions.'
	},
	{
		title: 'ITAM and License',
		detail: 'Entitlement and license posture are reviewed in the same workflow as cloud spend.'
	},
	{
		title: 'Platform Tooling',
		detail:
			'Observability and platform service costs are tied to operating owners and financial outcomes.'
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
