export const RAW_PUBLIC_CONTENT_RESOURCES = [
	{
		kind: 'resources',
		slug: 'enterprise-governance-overview',
		title: 'Enterprise Governance Overview',
		summary:
			'Understand the enterprise buying lane across governance, procurement, rollout design, and operating controls.',
		kicker: 'Resource',
		seoTitle: 'Enterprise Governance Overview',
		seoDescription:
			'Review the enterprise governance lane for Valdrics, including procurement, security review, and rollout expectations.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'evaluate',
		readingMinutes: 4,
		audiences: ['procurement', 'security', 'executive'],
		primaryCta: { label: 'Open Enterprise Page', href: '/enterprise' },
		secondaryCta: { label: 'Talk to Sales', href: '/talk-to-sales' },
		sections: [
			{
				title: 'When to use the enterprise lane',
				body: [
					'Use the enterprise lane when security review, procurement diligence, SSO or SCIM expectations, or staged rollout controls need a dedicated path.',
					'The goal is to separate fast product evaluation from formal organizational review when those motions need different participants.'
				],
				bullets: [
					'Security and identity review',
					'Commercial and procurement review',
					'Rollout planning for complex environments'
				]
			},
			{
				title: 'What buyers should expect',
				body: [
					'Enterprise review should clarify scope, responsibilities, access posture, and evidence expectations before activation expands.',
					'That keeps the commercial path aligned with the operating model instead of treating them as separate conversations.'
				],
				bullets: [
					'Named stakeholders for review',
					'A shared diligence packet',
					'An explicit rollout path'
				]
			}
		],
		related: [
			{ kind: 'proof', slug: 'validation-scope-and-operational-hardening' },
			{ kind: 'resources', slug: 'executive-one-pager' }
		]
	},
	{
		kind: 'resources',
		slug: 'cloud-waste-review-checklist',
		title: 'Cloud Waste Review Checklist',
		summary:
			'Run a weekly 30-minute operating review that moves material spend issues into named ownership and explicit action.',
		kicker: 'Checklist',
		seoTitle: 'Cloud Waste Review Checklist',
		seoDescription:
			'Use this cloud waste review checklist to run a weekly cross-functional spend review without ad hoc escalation.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'learn',
		readingMinutes: 5,
		audiences: ['engineering', 'finance', 'platform'],
		primaryCta: { label: 'Start Free', href: '/auth/login?intent=resource_signup&entry=resources' },
		secondaryCta: { label: 'Open Docs', href: '/docs' },
		sections: [
			{
				title: 'What a weekly review should do',
				body: [
					'A good weekly review is not a scoreboard meeting. It is the moment where material issues are scoped, assigned, and routed with enough context to act.',
					'That is how teams reduce late-month surprises without creating a heavy meeting ritual.'
				],
				bullets: [
					'Review the highest-signal issues first',
					'Assign one accountable owner per material issue',
					'Set explicit next action and due date'
				]
			},
			{
				title: 'What to avoid',
				body: [
					'Do not try to review every low-value anomaly or make the meeting into a generic report-out.',
					'The meeting should exist to move action forward, not to repeat what people already know.'
				],
				bullets: [
					'Too many issues in one pass',
					'No clear owner handoff',
					'No preserved record of the decision'
				]
			}
		],
		related: [
			{ kind: 'insights', slug: 'how-to-run-a-weekly-waste-review' },
			{ kind: 'docs', slug: 'owner-routing-and-approval-path' }
		]
	},
	{
		kind: 'resources',
		slug: 'greenops-decision-framework',
		title: 'GreenOps Decision Framework',
		summary:
			'Balance cost, carbon, and reliability with one reviewable decision path instead of disconnected sustainability reporting.',
		kicker: 'Guide',
		seoTitle: 'GreenOps Decision Framework',
		seoDescription:
			'Use a GreenOps decision framework that balances cost, carbon, and reliability in one reviewable operating loop.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'learn',
		readingMinutes: 6,
		audiences: ['platform', 'engineering', 'executive'],
		primaryCta: { label: 'Open GreenOps', href: '/greenops' },
		secondaryCta: { label: 'Open Insights', href: '/insights' },
		sections: [
			{
				title: 'Treat carbon as a decision input, not a separate dashboard',
				body: [
					'The operational value of GreenOps comes from joining carbon context to the same owner, risk, and execution path as spend action.',
					'That keeps teams from choosing between budget pressure and cleaner-runtime decisions without enough context.'
				],
				bullets: [
					'Cost, carbon, and reliability are reviewed together',
					'Tradeoffs stay explicit',
					'Actions remain reviewable after execution'
				]
			},
			{
				title: 'What a buyer-safe framework looks like',
				body: [
					'The framework should show who owns the decision, what guardrails apply, and what evidence remains afterward.',
					'That gives platform and leadership teams one narrative instead of multiple competing reports.'
				],
				bullets: ['Named owner', 'Clear decision gate', 'Recorded outcome']
			}
		],
		related: [
			{ kind: 'insights', slug: 'why-detection-without-ownership-fails' },
			{ kind: 'proof', slug: 'safe-access-model' }
		]
	},
	{
		kind: 'resources',
		slug: 'saas-license-governance-starter-pack',
		title: 'SaaS and License Governance Starter Pack',
		summary:
			'Start software renewal and license-rightsizing reviews with owner routing, approval context, and a cleaner record for finance review.',
		kicker: 'Template',
		seoTitle: 'SaaS and License Governance Starter Pack',
		seoDescription:
			'Use a SaaS and license governance starter pack for software renewals, owner routing, and finance-ready decision context.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'evaluate',
		readingMinutes: 5,
		audiences: ['finance', 'procurement', 'engineering'],
		primaryCta: { label: 'Open Technical Validation', href: '/docs/technical-validation' },
		secondaryCta: { label: 'View Pricing', href: '/pricing' },
		sections: [
			{
				title: 'Where software decisions usually break',
				body: [
					'Software and license reviews often break because procurement, finance, engineering, and app owners each see only part of the context.',
					'The operating loop has to preserve ownership and approval context so the decision survives renewal pressure.'
				],
				bullets: [
					'App owners need the affected context',
					'Finance needs the cost frame',
					'Procurement needs a record that is easy to reuse'
				]
			},
			{
				title: 'What the starter pack is meant to prove',
				body: [
					'The starter pack helps teams show that software governance can be run as a repeatable workflow instead of a scattered month-end exercise.',
					'That matters before a buyer expands into deeper automation or enterprise diligence.'
				],
				bullets: [
					'Cleaner weekly review loops',
					'Clearer ownership before renewals',
					'Better reuse of the decision record'
				]
			}
		],
		related: [
			{ kind: 'docs', slug: 'decision-history-and-export-records' },
			{ kind: 'proof', slug: 'identity-and-approval-controls' }
		]
	},
	{
		kind: 'resources',
		slug: 'executive-one-pager',
		title: 'Executive One-Pager',
		summary:
			'Use the one-pager when leadership, finance, or procurement needs the short version of the operating model and rollout path.',
		kicker: 'Collateral',
		seoTitle: 'Executive One-Pager',
		seoDescription:
			'Download the Valdrics executive one-pager for finance, engineering, and procurement alignment.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'evaluate',
		readingMinutes: 3,
		audiences: ['executive', 'finance', 'procurement'],
		primaryCta: {
			label: 'Download One-Pager',
			href: '/resources/valdrics-enterprise-one-pager.md'
		},
		secondaryCta: { label: 'Open Enterprise Page', href: '/enterprise' },
		downloads: [
			{
				label: 'Executive One-Pager (Markdown)',
				href: '/resources/valdrics-enterprise-one-pager.md'
			}
		],
		sections: [
			{
				title: 'When to use it',
				body: [
					'Use the one-pager when a stakeholder needs the product, rollout, and governance story quickly without reading a deeper packet.',
					'It works best as a pre-read before a diligence or pricing conversation.'
				],
				bullets: ['Leadership pre-read', 'Procurement overview', 'Internal alignment note']
			},
			{
				title: 'What it should answer',
				body: [
					'The one-pager should answer what Valdrics coordinates, how teams start, and why the operating model is different from a pure visibility tool.',
					'It should not try to carry the full technical validation burden on its own.'
				],
				bullets: ['What the product is', 'Who it is for', 'How a first rollout usually starts']
			}
		],
		related: [
			{ kind: 'resources', slug: 'enterprise-governance-overview' },
			{ kind: 'proof', slug: 'validation-scope-and-operational-hardening' }
		]
	},
	{
		kind: 'resources',
		slug: 'roi-assumptions',
		title: 'ROI Assumptions Worksheet',
		summary:
			'Review the planning assumptions behind the simulator so finance and engineering can pressure-test the modeled range before procurement review.',
		kicker: 'Worksheet',
		seoTitle: 'ROI Assumptions Worksheet',
		seoDescription:
			'Download the ROI assumptions worksheet used in the Valdrics simulator and planning discussions.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'validate',
		readingMinutes: 3,
		audiences: ['finance', 'executive'],
		primaryCta: { label: 'Download Worksheet', href: '/resources/valdrics-roi-assumptions.csv' },
		secondaryCta: { label: 'Open Pricing', href: '/pricing' },
		downloads: [
			{ label: 'ROI Assumptions Worksheet (CSV)', href: '/resources/valdrics-roi-assumptions.csv' }
		],
		sections: [
			{
				title: 'What this worksheet is for',
				body: [
					'The worksheet turns the simulator into a reviewable planning artifact so finance and engineering can agree on the assumptions before using the model in a buying discussion.',
					'That helps keep the landing claim grounded without overloading the hero.'
				],
				bullets: [
					'Modeled spend assumptions',
					'Recovery-range planning inputs',
					'Rollout and timeline review'
				]
			},
			{
				title: 'How to use it well',
				body: [
					'Use the worksheet to refine a decision, not to manufacture certainty where the team still lacks operational evidence.',
					'The most useful buyers pair the worksheet with one live workflow demonstration.'
				],
				bullets: [
					'Validate assumptions with real owners',
					'Use it as a discussion tool',
					'Pair it with the product walkthrough'
				]
			}
		],
		related: [
			{ kind: 'insights', slug: 'from-alert-to-approved-action' },
			{ kind: 'resources', slug: 'executive-one-pager' }
		]
	},
	{
		kind: 'resources',
		slug: 'global-finops-compliance-workbook',
		title: 'Global FinOps Compliance Workbook',
		summary:
			'Use the workbook when diligence needs a buyer-friendly checklist that connects controls, operations, and rollout assumptions.',
		kicker: 'Workbook',
		seoTitle: 'Global FinOps Compliance Workbook',
		seoDescription:
			'Download the Valdrics compliance workbook for security, procurement, and governance review.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'validate',
		readingMinutes: 4,
		audiences: ['security', 'procurement', 'finance'],
		primaryCta: {
			label: 'Download Workbook',
			href: '/resources/global-finops-compliance-workbook.md'
		},
		secondaryCta: { label: 'Talk to Sales', href: '/talk-to-sales' },
		downloads: [
			{
				label: 'Compliance Workbook (Markdown)',
				href: '/resources/global-finops-compliance-workbook.md'
			}
		],
		sections: [
			{
				title: 'Why this workbook exists',
				body: [
					'Security and procurement reviews move faster when the buyer can inspect a structured checklist instead of pulling answers from many short calls.',
					'The workbook packages those concerns into one public artifact.'
				],
				bullets: [
					'Security review framing',
					'Governance and operating model questions',
					'Rollout-readiness prompts'
				]
			},
			{
				title: 'How it complements the product',
				body: [
					'The workbook should complement real product proof, not replace it. Buyers still need to see what the system coordinates between alert and action.',
					'That is why it pairs well with the decision-loop demo and proof pages.'
				],
				bullets: [
					'Use it alongside proof pages',
					'Use it before enterprise briefing',
					'Use it to align procurement stakeholders'
				]
			}
		],
		related: [
			{ kind: 'proof', slug: 'validation-scope-and-operational-hardening' },
			{ kind: 'resources', slug: 'enterprise-governance-overview' }
		]
	}
] as const;
