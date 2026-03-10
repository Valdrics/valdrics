export const RAW_PUBLIC_CONTENT_DOCS = [
	{
		kind: 'docs',
		slug: 'quick-start-workspace',
		title: 'Quick Start a Valdrics Workspace',
		summary:
			'Launch your first workspace, connect your first data source, and route your first spend decision without a heavy implementation cycle.',
		kicker: 'Documentation',
		seoTitle: 'Quick Start a Valdrics Workspace',
		seoDescription:
			'Follow the fastest path from empty workspace to your first owner-routed cloud or software decision in Valdrics.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'evaluate',
		readingMinutes: 5,
		audiences: ['engineering', 'finance', 'platform'],
		primaryCta: { label: 'Start Free Workspace', href: '/auth/login?mode=signup' },
		secondaryCta: { label: 'Open Pricing', href: '/pricing' },
		sections: [
			{
				title: 'What this quick start covers',
				body: [
					'Valdrics is designed to get one real decision loop live quickly, not to make teams wait through a long dashboard setup project.',
					'The first milestone is simple: connect one source, surface one material issue, attach the right owner, and capture the decision record.'
				],
				bullets: [
					'Create a workspace and choose the first buying path',
					'Connect the first provider or operating surface',
					'Route the first issue to a named owner',
					'Record the outcome for finance and leadership review'
				]
			},
			{
				title: 'How teams usually start',
				body: [
					'The best starting point is the workload or software area where overspend, ownership confusion, or late escalation already hurts.',
					'That keeps the first workflow concrete and gives the team a measurable proof point before they expand provider coverage.'
				],
				bullets: [
					'Choose a high-friction cost area instead of trying to map everything at once',
					'Name one engineering or platform owner and one finance or FinOps reviewer',
					'Keep the first rollout focused on one recurring decision pattern'
				]
			}
		],
		related: [
			{ kind: 'docs', slug: 'owner-routing-and-approval-path' },
			{ kind: 'proof', slug: 'safe-access-model' }
		]
	},
	{
		kind: 'docs',
		slug: 'connect-first-provider',
		title: 'Connect the First Provider',
		summary:
			'Use the first provider connection to prove signal quality, review access posture, and establish the operating context for downstream decisions.',
		kicker: 'Documentation',
		seoTitle: 'Connect the First Provider',
		seoDescription:
			'Review the first-provider connection path for Valdrics, including access posture and first-workflow setup expectations.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'evaluate',
		readingMinutes: 4,
		audiences: ['engineering', 'platform', 'security'],
		primaryCta: { label: 'Open Technical Validation', href: '/docs/technical-validation' },
		secondaryCta: { label: 'View Proof Pack', href: '/proof' },
		sections: [
			{
				title: 'Use the first connection to prove trust, not breadth',
				body: [
					'The first connection should answer the buyer-safe questions early: what access is required, what context becomes visible, and what proof survives after action.',
					'Starting small reduces integration risk and gives security and platform teams a real review surface.'
				],
				bullets: [
					'Confirm the access model before enabling broad coverage',
					'Validate that spend signals map to a real owner queue',
					'Check that approval and export records are retained correctly'
				]
			},
			{
				title: 'What good first-connection evidence looks like',
				body: [
					'Buyers should be able to see one issue move from raw signal into an owner-routed decision path with context preserved.',
					'That evidence matters more than a large connector count during the first review.'
				],
				bullets: [
					'Named owner attached',
					'Checks or policy context attached',
					'Outcome and savings proof recorded'
				]
			}
		],
		related: [
			{ kind: 'proof', slug: 'identity-and-approval-controls' },
			{ kind: 'docs', slug: 'decision-history-and-export-records' }
		]
	},
	{
		kind: 'docs',
		slug: 'owner-routing-and-approval-path',
		title: 'Owner Routing and Approval Path',
		summary:
			'Make every material spend issue land with a named owner, clear approval context, and a reviewable next action.',
		kicker: 'Documentation',
		seoTitle: 'Owner Routing and Approval Path',
		seoDescription:
			'See how Valdrics routes spend issues to named owners and keeps checks attached before action moves.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'validate',
		readingMinutes: 6,
		audiences: ['engineering', 'finance', 'platform'],
		primaryCta: { label: 'See the Decision Loop', href: '/#signal-map' },
		secondaryCta: { label: 'Talk to Sales', href: '/talk-to-sales' },
		sections: [
			{
				title: 'Why routing matters',
				body: [
					'Most teams do not fail because they lack another spend chart. They fail because the issue reaches the wrong person too late or without enough context to act safely.',
					'Valdrics treats the handoff itself as part of the product surface.'
				],
				bullets: [
					'The issue lands with a named decision owner',
					'Checks stay attached before the conversation starts',
					'Approvals are explicit instead of implied in chat threads'
				]
			},
			{
				title: 'What the approval path should preserve',
				body: [
					'The approval path should retain the original signal, the current gate, and the final outcome in one reviewable chain.',
					'That is what lets finance, platform, and leadership review the decision later without reconstructing context.'
				],
				bullets: [
					'Signal source and severity',
					'Owner and reviewer assignment',
					'Rationale and recorded result'
				]
			}
		],
		related: [
			{ kind: 'insights', slug: 'from-alert-to-approved-action' },
			{ kind: 'proof', slug: 'decision-history-and-export-integrity' }
		]
	},
	{
		kind: 'docs',
		slug: 'decision-history-and-export-records',
		title: 'Decision History and Export Records',
		summary:
			'Keep a durable record of what changed, who approved it, and what outcome was captured after action.',
		kicker: 'Documentation',
		seoTitle: 'Decision History and Export Records',
		seoDescription:
			'Understand how Valdrics records decisions, approvals, and export-ready evidence for later review.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'validate',
		readingMinutes: 5,
		audiences: ['finance', 'security', 'executive'],
		primaryCta: { label: 'Open Proof Pack', href: '/proof' },
		secondaryCta: {
			label: 'Download One-Pager',
			href: '/resources/valdrics-enterprise-one-pager.md'
		},
		sections: [
			{
				title: 'Record what buyers actually need later',
				body: [
					'The useful record is not just that a recommendation existed. It is that the issue, owner, gate, and result can be reviewed together after the meeting.',
					'That supports finance reviews, security review, and leadership reporting without extra narrative reconstruction.'
				],
				bullets: [
					'Decision context survives handoff',
					'Outcome proof is linked to the original issue',
					'Export-ready records reduce diligence friction'
				]
			},
			{
				title: 'When teams use exports',
				body: [
					'Export surfaces are most useful when an internal reviewer or buyer asks for proof without needing direct product access.',
					'That includes procurement packets, leadership review decks, and finance close support.'
				],
				bullets: [
					'Internal operating reviews',
					'Buyer diligence and security review',
					'Executive summaries and evidence packs'
				]
			}
		],
		related: [
			{ kind: 'proof', slug: 'decision-history-and-export-integrity' },
			{ kind: 'resources', slug: 'executive-one-pager' }
		]
	}
] as const;
