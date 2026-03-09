export const RAW_PUBLIC_CONTENT_INSIGHTS = [
	{
		kind: 'insights',
		slug: 'why-detection-without-ownership-fails',
		title: 'Why Detection Without Ownership Fails',
		summary: 'Overspend still compounds when a signal appears on time but no one owns the next move clearly enough to act.',
		kicker: 'Insight',
		seoTitle: 'Why Detection Without Ownership Fails',
		seoDescription: 'Understand why spend detection alone does not prevent waste when ownership and approval are still ambiguous.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'learn',
		readingMinutes: 6,
		audiences: ['engineering', 'finance', 'executive'],
		primaryCta: { label: 'Start Free', href: '/auth/login?intent=insights_signup' },
		secondaryCta: { label: 'Open Resources', href: '/resources' },
		sections: [
			{
				title: 'The reporting trap',
				body: [
					'Teams often invest in better visibility and still arrive at the same month-end tension because the issue never becomes a clearly owned decision.',
					'The signal exists, but the operating system around it does not.'
				],
				bullets: [
					'No named owner',
					'No shared approval path',
					'No reusable record of the final decision'
				]
			},
			{
				title: 'What actually changes the outcome',
				body: [
					'The material change happens when the same issue carries enough context to move from detection into accountable action without losing trust.',
					'That is why Valdrics emphasizes owner routing and recorded outcomes instead of only surfacing another anomaly feed.'
				],
				bullets: [
					'Signal scoped to the right context',
					'Owner assigned before debate expands',
					'Outcome captured when the change lands'
				]
			}
		],
		related: [
			{ kind: 'docs', slug: 'owner-routing-and-approval-path' },
			{ kind: 'proof', slug: 'decision-history-and-export-integrity' }
		]
	},
	{
		kind: 'insights',
		slug: 'how-to-run-a-weekly-waste-review',
		title: 'How to Run a Weekly Waste Review',
		summary: 'A weekly review works best when it is short, owner-driven, and focused on moving decisions forward rather than reciting KPIs.',
		kicker: 'Insight',
		seoTitle: 'How to Run a Weekly Waste Review',
		seoDescription: 'Run a weekly waste review that keeps engineering and finance aligned on priority issues and next actions.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'learn',
		readingMinutes: 5,
		audiences: ['engineering', 'finance', 'platform'],
		primaryCta: { label: 'Open Checklist', href: '/resources/cloud-waste-review-checklist' },
		secondaryCta: { label: 'See Pricing', href: '/pricing' },
		sections: [
			{
				title: 'The purpose of the meeting',
				body: [
					'The meeting should exist to move the highest-value issues into a clear owner and next action. It should not try to solve everything or restate dashboard facts.',
					'When the meeting becomes too broad, the action quality collapses.'
				],
				bullets: [
					'Limit the issue set',
					'Keep an explicit owner per issue',
					'Close each item with a clear next step'
				]
			},
			{
				title: 'How a review stays useful',
				body: [
					'The meeting stays useful when the decision history survives after the call. That prevents teams from repeating the same debate in different channels.',
					'The workflow matters more than the slide count.'
				],
				bullets: [
					'Carry the signal context into the meeting',
					'Preserve the decision after the meeting',
					'Share one record with finance and engineering'
				]
			}
		],
		related: [
			{ kind: 'resources', slug: 'cloud-waste-review-checklist' },
			{ kind: 'docs', slug: 'decision-history-and-export-records' }
		]
	},
	{
		kind: 'insights',
		slug: 'from-alert-to-approved-action',
		title: 'From Alert to Approved Action',
		summary: 'The real conversion point is when an issue becomes an approved action path, not when a chart turns red.',
		kicker: 'Insight',
		seoTitle: 'From Alert to Approved Action',
		seoDescription: 'Move from alert to approved action with explicit owner routing, checks, and recorded outcomes.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'evaluate',
		readingMinutes: 6,
		audiences: ['engineering', 'finance', 'procurement'],
		primaryCta: { label: 'See the Decision Loop', href: '/#signal-map' },
		secondaryCta: { label: 'Talk to Sales', href: '/talk-to-sales' },
		sections: [
			{
				title: 'Where the commercial story changes',
				body: [
					'Commodity tools usually stop at alerting or recommendations. The stronger operating story begins when the issue becomes a controlled action path.',
					'That is where finance and engineering start trusting the system as a decision layer rather than another reporting screen.'
				],
				bullets: [
					'Signal scoped',
					'Checks applied',
					'Approval routed',
					'Outcome recorded'
				]
			},
			{
				title: 'Why this matters in evaluation',
				body: [
					'Buyers need to see the full path because it shortens the mental gap between product demo and real rollout.',
					'The more concrete that path looks, the less the sales process depends on abstract explanation.'
				],
				bullets: [
					'Clearer product comprehension',
					'Less sales friction',
					'Stronger internal buyer retelling'
				]
			}
		],
		related: [
			{ kind: 'docs', slug: 'owner-routing-and-approval-path' },
			{ kind: 'proof', slug: 'identity-and-approval-controls' }
		]
	}
] as const;
