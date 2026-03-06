import type { BuyerPersona } from '$lib/landing/landingExperiment';

export const HERO_ROLE_CONTEXT: Record<
	BuyerPersona,
	{
		controlTitle: string;
		metricsTitle: string;
		subtitle: string;
		quantPromise: string;
		primaryIntent: string;
	}
> = Object.freeze({
	cto: {
		controlTitle: 'Stop cloud and software waste before it slows your roadmap.',
		metricsTitle: 'From cost dashboards to fast, owner-led engineering action.',
		subtitle:
			'Give engineering a faster path from spend signal to safe execution with clear ownership.',
		quantPromise: 'Target 10-18% controllable spend recovery opportunity in the first 90 days.',
		primaryIntent: 'engineering_control'
	},
	finops: {
		controlTitle: 'Control every dollar with accountable ownership and faster decisions.',
		metricsTitle: 'From visibility reporting to faster financial action.',
		subtitle:
			'Detect spend movement earlier, route accountable owners immediately, and close actions before month-end pressure.',
		quantPromise:
			'Target 30-50% fewer late-cycle escalations by formalizing ownership and action paths.',
		primaryIntent: 'finops_governance'
	},
	security: {
		controlTitle: 'Reduce spend and change risk without becoming a delivery bottleneck.',
		metricsTitle: 'From anomalies to safe, reviewable remediation.',
		subtitle:
			'Keep execution guarded by approvals and pre-change checks while engineering keeps shipping.',
		quantPromise:
			'Target measurable reduction in risky manual changes by enforcing pre-change checks.',
		primaryIntent: 'security_governance'
	},
	cfo: {
		controlTitle: 'Control cloud margin risk before it reaches the boardroom.',
		metricsTitle: 'From spend metrics to board-ready economic control.',
		subtitle:
			'Tie spend movement to accountable owners so margin conversations shift from surprise to strategy.',
		quantPromise:
			'Target stronger forecast confidence with one decision loop across engineering and finance.',
		primaryIntent: 'executive_briefing'
	}
});

export const HERO_PROOF_POINTS = Object.freeze([
	{
		title: 'One Economic Truth',
		detail: 'Cloud, SaaS, and license decisions share one operating view.'
	},
	{
		title: 'Execution With Guardrails',
		detail: 'Owners, approvals, and safety checks are built into every action path.'
	},
	{
		title: 'Global Compliance Proof',
		detail: 'SOC 2, GDPR, and ISO 27001 readiness alignment out of the box.'
	}
]);

export const HERO_OUTCOME_CHIPS = Object.freeze([
	{
		label: 'Signal-to-owner handoff',
		value: '< 1 business day target'
	},
	{
		label: 'Controllable waste opportunity',
		value: '10-18% target range'
	},
	{
		label: 'Operating model',
		value: 'Visibility + ownership + GreenOps'
	}
]);

export const ABOVE_FOLD_TRUST_BADGES = Object.freeze([
	'ISO 27001 readiness alignment',
	'SOC 2 program alignment',
	'GDPR data-rights support',
	'DORA operational resilience',
	'SSO + SCIM access controls',
	'Tenant-isolated workspaces'
]);

export const SIGNAL_VALUE_CARDS = Object.freeze([
	{
		label: 'Clarity',
		value: 'See what changed and why',
		hint: 'Cloud spend, anomaly, and workload signals in one operational view.'
	},
	{
		label: 'Ownership',
		value: 'Know who decides next',
		hint: 'Clear responsibility across platform, finance, and leadership.'
	},
	{
		label: 'Confidence',
		value: 'Explain decisions quickly',
		hint: 'Teams stay aligned during finance and leadership reviews.'
	}
]);

export const MICRO_DEMO_STEPS = Object.freeze([
	{
		id: 'detect',
		title: 'Detect',
		detail: 'Realtime cloud anomaly is detected and scoped to impacted workloads.'
	},
	{
		id: 'govern',
		title: 'Assess',
		detail: 'Risk checks and entitlement context evaluate blast radius before execution.'
	},
	{
		id: 'approve',
		title: 'Approve',
		detail: 'Accountable owner approves with explicit decision context and clear impact.'
	},
	{
		id: 'prove',
		title: 'Confirm',
		detail: 'Outcomes are captured so finance and engineering can measure impact quickly.'
	}
]);

export const CLOUD_HOOK_STATES = Object.freeze([
	{
		id: 'without',
		title: 'Without Valdrics',
		subtitle: 'Reactive cloud cost operations',
		ahaMoment: 'Anomalies surface late, ownership is unclear, and teams react under pressure.',
		points: [
			'Spend spikes are discovered after the billing cycle.',
			'Remediation ownership is ambiguous across teams.',
			'Cost actions execute ad hoc, and outcomes are hard to track.'
		],
		metrics: [
			{ label: 'Signal Lag', value: 'After invoice close' },
			{ label: 'Decision Owner', value: 'Unclear' },
			{ label: 'Execution Safety', value: 'Inconsistent' }
		]
	},
	{
		id: 'with',
		title: 'With Valdrics',
		subtitle: 'Controlled cloud economics',
		ahaMoment: 'Anomaly detected, owner assigned, risk checked, and action approved in one flow.',
		points: [
			'Realtime anomalies route to a named accountable owner.',
			'Safety checks run before every change.',
			'Decision history is easy to share with finance and leadership.'
		],
		metrics: [
			{ label: 'Signal Lag', value: 'Realtime' },
			{ label: 'Decision Owner', value: 'Explicit' },
			{ label: 'Execution Safety', value: 'Guardrailed' }
		]
	}
]);

export const EXECUTIVE_CONFIDENCE_POINTS = Object.freeze([
	{
		kicker: 'Decision Quality',
		title: 'Teams decide faster with less friction',
		detail: 'Economic controls are clear, reviewable, and consistently applied across teams.'
	},
	{
		kicker: 'Execution',
		title: 'Actions stay safe and accountable',
		detail: 'Change flows remain safe with clear ownership and explicit approvals.'
	},
	{
		kicker: 'Leadership',
		title: 'Reviews stay focused on outcomes',
		detail: 'Leadership gets a clear narrative from signal to action without noise.'
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

export const TRUST_BENCHMARK_OUTCOMES = Object.freeze([
	{
		title: 'Faster economic decisions',
		detail:
			'High-growth teams target a tighter detect-to-decision cycle by unifying ownership and execution context.',
		benchmark: 'Modeled benchmark range: 15-25% faster decision cycles'
	},
	{
		title: 'Fewer finance escalations',
		detail:
			'When ownership and approvals are explicit, month-end surprise escalations can be reduced materially.',
		benchmark: 'Modeled benchmark range: 30-50% fewer late escalations'
	},
	{
		title: 'Clear accountability',
		detail:
			'Teams can move from ambiguous remediation ownership to explicit, role-based accountability across functions.',
		benchmark: 'Modeled benchmark range: owner assigned on every material anomaly'
	}
]);

export const BUYER_ROLE_VIEWS = Object.freeze([
	{
		id: 'cto' as const,
		label: 'Engineering',
		headline: 'Keep roadmap velocity while controlling cloud and software spend',
		detail:
			'Engineering ships faster when spend risk is managed inside delivery workflows, not escalated after the close.',
		signals: ['Roadmap stability', 'Controlled velocity', 'Fewer escalation loops'],
		thirtyDayOutcomes: [
			'Top spend regressions mapped to accountable owners.',
			'High-risk actions routed through explicit owner sign-off.',
			'Weekly engineering reviews include cost + risk with clear next actions.'
		]
	},
	{
		id: 'finops' as const,
		label: 'FinOps',
		headline: 'Move from reporting to faster financial action',
		detail:
			'Use one operating loop to attribute spend movement, assign ownership, and route remediation clearly.',
		signals: ['Forecast confidence', 'Ownership clarity', 'Faster remediation cycle'],
		thirtyDayOutcomes: [
			'Material anomalies triaged with ownership and deadlines.',
			'Escalation volume reduced through earlier owner-led decisions.',
			'Finance and platform teams review one shared operating narrative.'
		]
	},
	{
		id: 'security' as const,
		label: 'Security',
		headline: 'Reduce risk without becoming a delivery bottleneck',
		detail: 'Run risk checks before execution with explicit ownership and a clear change history.',
		signals: ['Control adherence', 'Risk visibility', 'Decision traceability'],
		thirtyDayOutcomes: [
			'Risk checks applied before cost-impacting actions.',
			'Approval lineage made explicit for sensitive changes.',
			'Security and platform teams share one review trail.'
		]
	},
	{
		id: 'cfo' as const,
		label: 'CFO',
		headline: 'Protect gross margin with predictable spend decisions',
		detail:
			'Tie cloud actions to financial impact and ownership so executive decisions rely on controlled, trusted signals.',
		signals: ['Margin protection', 'Investment confidence', 'Board-level explainability'],
		thirtyDayOutcomes: [
			'Top margin risks linked to named owners and action dates.',
			'Forecast conversations shift from variance explanation to decision planning.',
			'Board updates include a concise signal-to-action narrative.'
		]
	}
]);

export const CUSTOMER_PROOF_STORIES = Object.freeze([
	{
		title: 'Growth B2B SaaS Platform',
		before: 'Monthly spikes were discovered late and routed through ad-hoc escalation threads.',
		after:
			'Ownership and approvals moved into weekly operating reviews with named decision owners.',
		impact:
			'Prelaunch design-partner signal: double-digit controllable spend opportunity surfaced before month-end close.'
	},
	{
		title: 'Digital Commerce Group',
		before: 'Finance and engineering escalations clustered around month-end close.',
		after: 'Spend issues were triaged weekly with clear owners and explicit action deadlines.',
		impact: 'Prelaunch design-partner signal: fewer late-cycle escalations and faster owner handoffs.'
	},
	{
		title: 'Multi-Region Platform Team',
		before: 'Cloud and SaaS actions were tracked in disconnected channels and ticket queues.',
		after: 'Cloud+, SaaS, and license decisions ran in one shared operating loop across teams.',
		impact:
			'Prelaunch design-partner signal: unified signal-to-action narrative for leadership reviews.'
	}
]);

export const PRELAUNCH_PROOF_NOTE =
	'Valdrics is prelaunch. Public customer logos and production outcome studies will be published after go-live. Current proof reflects design-partner sessions and modeled benchmark ranges.';
