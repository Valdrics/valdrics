export const RAW_PUBLIC_CONTENT_PROOF = [
	{
		kind: 'proof',
		slug: 'safe-access-model',
		title: 'Safe Access Model',
		summary:
			'Understand how Valdrics approaches buyer-safe access posture, early trust, and rollout proof without overclaiming prelaunch validation.',
		kicker: 'Proof Pack',
		seoTitle: 'Safe Access Model',
		seoDescription:
			'Review the safe-access model for Valdrics, including read-only posture where supported and rollout-safe access review.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'validate',
		readingMinutes: 5,
		audiences: ['security', 'platform', 'procurement'],
		primaryCta: { label: 'Open Technical Validation', href: '/docs/technical-validation' },
		secondaryCta: { label: 'Open Enterprise Path', href: '/enterprise' },
		sections: [
			{
				title: 'What buyers need early',
				body: [
					'Prelaunch buyers need an access story they can review safely before they ask for broader proof. The access conversation should lower risk, not create more uncertainty.',
					'That is why Valdrics emphasizes scoped access expectations and rollout-safe validation artifacts early.'
				],
				bullets: [
					'Read-only posture where supported',
					'Reviewable access checklist',
					'Clear path to first controlled workflow'
				]
			},
			{
				title: 'What this page is not claiming',
				body: [
					'This page is not a substitute for environment-specific security review, and it does not claim a blanket posture that every provider or workflow implements identically.',
					'It exists to make the first diligence conversation concrete and honest.'
				],
				bullets: [
					'Buyer-safe, not buyer-complacent',
					'Specific before broad',
					'Aligned with the enterprise diligence path'
				]
			}
		],
		related: [
			{ kind: 'resources', slug: 'global-finops-compliance-workbook' },
			{ kind: 'proof', slug: 'identity-and-approval-controls' }
		]
	},
	{
		kind: 'proof',
		slug: 'identity-and-approval-controls',
		title: 'Identity and Approval Controls',
		summary:
			'See how identity expectations, approval gates, and owner-routed execution fit together in the decision path.',
		kicker: 'Proof Pack',
		seoTitle: 'Identity and Approval Controls',
		seoDescription:
			'Review identity and approval controls in the Valdrics decision path, including owner routing and guarded action flow.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'validate',
		readingMinutes: 5,
		audiences: ['security', 'finance', 'platform'],
		primaryCta: { label: 'See the Decision Loop', href: '/#signal-map' },
		secondaryCta: { label: 'Open Enterprise Path', href: '/enterprise' },
		sections: [
			{
				title: 'Identity matters because accountability matters',
				body: [
					'Approval controls are only useful when the buyer can see who owns the issue, who reviews it, and what gate the issue is in right now.',
					'That turns approval from abstract governance language into an operationally reviewable chain.'
				],
				bullets: [
					'Named decision owner',
					'Explicit reviewer or approval path',
					'Recorded gate progression'
				]
			},
			{
				title: 'Why this reduces buyer risk',
				body: [
					'Buyers get more confidence when identity and approval are built into the action story instead of being stapled on afterward.',
					'That is especially important when security, finance, and engineering need to retell the product differently but trust the same underlying control path.'
				],
				bullets: [
					'Clearer internal retelling',
					'Better governance posture',
					'Stronger operational reviewability'
				]
			}
		],
		related: [
			{ kind: 'docs', slug: 'owner-routing-and-approval-path' },
			{ kind: 'proof', slug: 'decision-history-and-export-integrity' }
		]
	},
	{
		kind: 'proof',
		slug: 'decision-history-and-export-integrity',
		title: 'Decision History and Export Integrity',
		summary:
			'Review how Valdrics preserves the decision chain so the result can survive leadership, finance, and procurement review.',
		kicker: 'Proof Pack',
		seoTitle: 'Decision History and Export Integrity',
		seoDescription:
			'Understand how Valdrics preserves decision history and export-ready records for later buyer and operator review.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'validate',
		readingMinutes: 6,
		audiences: ['finance', 'executive', 'procurement'],
		primaryCta: { label: 'Open Documentation', href: '/docs' },
		secondaryCta: {
			label: 'Download Workbook',
			href: '/resources/global-finops-compliance-workbook.md'
		},
		sections: [
			{
				title: 'The record is part of the product',
				body: [
					'The decision record is not a side artifact. It is part of how the product proves that a material issue became a controlled action rather than a forgotten recommendation.',
					'That is why the export story matters during evaluation.'
				],
				bullets: [
					'Signal context stays attached',
					'Approval path stays visible',
					'Outcome proof survives the meeting'
				]
			},
			{
				title: 'What integrity means here',
				body: [
					'Integrity means the buyer can review the chain coherently later, not that every export replaces a formal audit product on its own.',
					'The useful question is whether the record remains understandable and trustworthy when it leaves the workflow.'
				],
				bullets: [
					'Readable outside the original meeting',
					'Reused in buyer diligence',
					'Helpful to finance and leadership'
				]
			}
		],
		related: [
			{ kind: 'docs', slug: 'decision-history-and-export-records' },
			{ kind: 'resources', slug: 'executive-one-pager' }
		]
	},
	{
		kind: 'proof',
		slug: 'validation-scope-and-operational-hardening',
		title: 'Validation Scope and Operational Hardening',
		summary:
			'Understand what the current public validation materials are meant to prove and where they fit in a prelaunch diligence cycle.',
		kicker: 'Proof Pack',
		seoTitle: 'Validation Scope and Operational Hardening',
		seoDescription:
			'Review the public validation scope and operational hardening story for Valdrics.',
		updatedAt: '2026-03-09T00:00:00.000Z',
		stage: 'validate',
		readingMinutes: 5,
		audiences: ['executive', 'security', 'procurement'],
		primaryCta: { label: 'Open Technical Validation', href: '/docs/technical-validation' },
		secondaryCta: {
			label: 'Download Executive One-Pager',
			href: '/resources/valdrics-enterprise-one-pager.md'
		},
		sections: [
			{
				title: 'What public validation should do',
				body: [
					'Public validation should reduce ambiguity and give buyers a concrete review surface. It should not overstate prelaunch proof or imply customer evidence that does not exist yet.',
					'The right balance is honest scope, clear architecture, and visible operational discipline.'
				],
				bullets: [
					'Show what can be verified now',
					'Avoid fake launch-stage proof',
					'Link marketing to operational reality'
				]
			},
			{
				title: 'What hardening looks like on the public surface',
				body: [
					'Operational hardening includes route integrity, reduced-motion behavior, safe telemetry boundaries, and deterministic page behavior that does not fall apart under real traffic.',
					'Those signals matter because buyers judge discipline from the public surface too.'
				],
				bullets: [
					'Accessible motion patterns',
					'Stable public route behavior',
					'Clear proof-to-doc transitions'
				]
			}
		],
		related: [
			{ kind: 'proof', slug: 'safe-access-model' },
			{ kind: 'resources', slug: 'global-finops-compliance-workbook' }
		]
	}
] as const;
