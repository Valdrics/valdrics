import type { BuyerPersona } from '$lib/landing/landingExperiment';

export const HERO_ROLE_CONTEXT: Record<
	BuyerPersona,
	{
		controlTitle: string;
		metricsTitle: string;
		subtitle: string;
		primaryIntent: string;
	}
> = Object.freeze({
	cto: {
		controlTitle:
			'Turn cloud, SaaS, and software spend into governed action without slowing delivery.',
		metricsTitle: 'From dashboards and tickets to one governed spend action system.',
		subtitle:
			'Valdrics turns cost, usage, and policy signals into owner-routed approvals, workflow execution, and exportable proof across cloud and software environments.',
		primaryIntent: 'engineering_control'
	},
	finops: {
		controlTitle: 'Move from spend visibility to owner-routed action across cloud and software.',
		metricsTitle: 'From spend reporting to one governed action path.',
		subtitle:
			'Valdrics connects anomalies, chargeback, remediation, and savings proof so finance and engineering work from one decision system.',
		primaryIntent: 'finops_governance'
	},
	security: {
		controlTitle:
			'Control cost-changing actions with approvals, workflow routing, and audit-ready proof.',
		metricsTitle: 'From spend anomalies to controlled execution.',
		subtitle:
			'Valdrics keeps policy checks, approval lineage, and decision evidence attached before spend-changing actions move.',
		primaryIntent: 'security_governance'
	},
	cfo: {
		controlTitle:
			'Protect margin with one governed system for cloud, SaaS, and software decisions.',
		metricsTitle: 'From variance reporting to board-ready action and proof.',
		subtitle:
			'Valdrics ties spend movement to accountable owners, approvals, and measurable proof before variance turns into board-level noise.',
		primaryIntent: 'executive_briefing'
	}
});

export const HERO_PROOF_POINTS = Object.freeze([
	{
		title: 'One Governed Operating Layer',
		detail: 'Cloud, SaaS, and software decisions share one control loop.'
	},
	{
		title: 'Owner-Routed Action',
		detail: 'Signals move with named owners, approvals, and deadlines instead of ad hoc follow-up.'
	},
	{
		title: 'Reviewable Outcomes',
		detail: 'Finance, security, and leadership can review one clean decision trail.'
	}
]);

export const HERO_OUTCOME_CHIPS = Object.freeze([
	{
		label: 'Signal-to-owner handoff',
		value: '< 1 business day target'
	},
	{
		label: 'Action path',
		value: 'Checks + approvals attached'
	},
	{
		label: 'Operating scope',
		value: 'Cloud + SaaS + software'
	}
]);

export const ABOVE_FOLD_TRUST_RAIL = Object.freeze([
	{
		title: 'Cloud + SaaS + software in one control layer',
		detail: 'Cost, usage, policy, and remediation records stay in one governed operating path.'
	},
	{
		title: 'Read-only onboarding where supported',
		detail:
			'Read-only cloud roles are used where supported. Connector secrets stay encrypted at rest.'
	},
	{
		title: 'Approval trail and exportable proof',
		detail: 'Decision history and export-ready records support finance, security, and buyer review.'
	}
]);

export const SIGNAL_VALUE_CARDS = Object.freeze([
	{
		label: 'Owner assigned',
		value: 'Every issue lands with a named decision owner',
		hint: 'Workload, team, and escalation context stay attached from first signal.'
	},
	{
		label: 'Approval path',
		value: 'Checks stay attached before action moves',
		hint: 'Finance, platform, and security review one guardrailed path.'
	},
	{
		label: 'Outcome recorded',
		value: 'Savings proof survives the meeting',
		hint: 'Leadership reviews the result, rationale, and exported record in one place.'
	}
]);

export const MICRO_DEMO_STEPS = Object.freeze([
	{
		id: 'detect',
		title: 'Scoped',
		detail: 'The signal is tagged to the affected workload, owner queue, and spend context.'
	},
	{
		id: 'govern',
		title: 'Routed',
		detail:
			'The issue moves to the right owner and review path before teams split into side threads.'
	},
	{
		id: 'approve',
		title: 'Approved',
		detail: 'Checks and approvers stay attached so the action can move with explicit sign-off.'
	},
	{
		id: 'prove',
		title: 'Recorded',
		detail: 'The result, rationale, and savings proof are saved for finance and leadership review.'
	}
]);

export const CLOUD_HOOK_STATES = Object.freeze([
	{
		id: 'without',
		title: 'Without Valdrics',
		subtitle: 'Dashboards, tickets, and side threads',
		ahaMoment:
			'The alert appears, but the team still has to figure out owner, risk, approval, and proof across separate systems.',
		points: [
			'Detection lives in one tool, ticketing in another, and proof in a spreadsheet or slide.',
			'The accountable owner is negotiated after the alert instead of assigned at ingest.',
			'Finance and engineering reconstruct the decision later when someone asks what happened.'
		],
		metrics: [
			{ label: 'Systems Touched', value: '4+' },
			{ label: 'Decision Owner', value: 'Negotiated' },
			{ label: 'Proof Quality', value: 'Fragmented' }
		]
	},
	{
		id: 'with',
		title: 'With Valdrics',
		subtitle: 'One governed action path',
		ahaMoment:
			'The issue is scoped once, routed to the right owner, moved through approvals, and kept as one reviewable record.',
		points: [
			'Owner, policy, and approval path are attached the moment the issue is created.',
			'Slack, Jira, Teams, and workflow automation move the work without losing governance.',
			'The final action keeps rationale, savings proof, and export-ready records for review.'
		],
		metrics: [
			{ label: 'Systems Touched', value: '1 operating layer' },
			{ label: 'Decision Owner', value: 'Assigned at ingest' },
			{ label: 'Proof Quality', value: 'Reviewable + exportable' }
		]
	}
]);

export const EXECUTIVE_CONFIDENCE_POINTS = Object.freeze([
	{
		kicker: 'Decision Proof',
		title: 'Every material action keeps owner, approval, and savings evidence',
		detail:
			'Finance, engineering, and security can review the same record instead of reconstructing events from chat threads and spreadsheets.'
	},
	{
		kicker: 'Operational Fit',
		title: 'Cross-functional teams work from one governed system',
		detail:
			'Cloud, SaaS, software, and carbon decisions move through one owner-routed path instead of separate tools and handoffs.'
	},
	{
		kicker: 'Rollout Confidence',
		title: 'The first controlled workflow lands without a services-heavy rollout',
		detail:
			'Teams can start with one controlled workflow, then expand into finance-grade rollout when procurement and governance depth increase.'
	}
]);

export const TRUST_ECOSYSTEM_BADGES = Object.freeze([
	'AWS',
	'Azure',
	'GCP',
	'Microsoft 365',
	'Salesforce',
	'Datadog',
	'Kubernetes'
]);

export const BUYER_ROLE_VIEWS = Object.freeze([
	{
		id: 'cto' as const,
		label: 'Engineering',
		headline: 'Keep delivery moving while turning spend signals into governed action',
		detail:
			'Engineering moves faster when cost risk is handled inside the operating path instead of escalated after finance close.',
		signals: ['Roadmap stability', 'Controlled velocity', 'Fewer escalation loops'],
		thirtyDayOutcomes: [
			'Top spend regressions mapped to accountable owners and workflow routes.',
			'High-risk changes move through explicit owner and policy sign-off.',
			'Weekly engineering reviews include cost, risk, and recorded actions in one view.'
		]
	},
	{
		id: 'finops' as const,
		label: 'FinOps',
		headline: 'Move from reporting to governed financial action across every spend surface',
		detail:
			'Use one operating system to attribute spend movement, assign ownership, route action, and keep savings proof intact.',
		signals: ['Forecast confidence', 'Ownership clarity', 'Faster remediation cycle'],
		thirtyDayOutcomes: [
			'Material anomalies triaged with ownership, approval lane, and deadlines.',
			'Escalation volume reduced through earlier owner-led decisions.',
			'Finance and platform teams review one shared operating narrative with proof.'
		]
	},
	{
		id: 'security' as const,
		label: 'Security',
		headline: 'Reduce risk without becoming the handoff bottleneck',
		detail:
			'Run risk checks before execution with explicit ownership, workflow routing, and clear decision history.',
		signals: ['Control adherence', 'Risk visibility', 'Decision traceability'],
		thirtyDayOutcomes: [
			'Risk checks applied before cost-impacting actions move.',
			'Approval lineage made explicit for sensitive changes and workflow dispatch.',
			'Security and platform teams share one review trail and exportable evidence set.'
		]
	},
	{
		id: 'cfo' as const,
		label: 'CFO',
		headline: 'Protect gross margin with predictable, reviewable spend decisions',
		detail:
			'Tie cloud and software actions to financial impact, ownership, and proof so executive decisions rely on controlled signals instead of after-the-fact explanations.',
		signals: ['Margin protection', 'Investment confidence', 'Board-level explainability'],
		thirtyDayOutcomes: [
			'Top margin risks linked to named owners, approval dates, and action status.',
			'Forecast conversations shift from variance explanation to decision planning.',
			'Board updates include a concise signal-to-action narrative with evidence.'
		]
	}
]);
