export type PublicTeamMember = {
	name: string;
	role: string;
	shortBio: string;
	photoAssetPath?: string;
	linkedinHref?: string;
};

export type DeploymentResidencyFact = {
	question: string;
	answer: string;
	status: 'current' | 'enterprise' | 'planned';
};

export const PUBLIC_TEAM_MEMBERS: readonly PublicTeamMember[] = Object.freeze([
	{
		name: 'AbdulGoniyy Dare',
		role: 'Founder',
		shortBio:
			'Building Valdrics around owner-routed action, approvals, and decision proof so cloud, SaaS, and software spend can move from signal to governed execution.'
	}
]);

export const PUBLIC_DEPLOYMENT_RESIDENCY_FACTS: readonly DeploymentResidencyFact[] = Object.freeze([
	{
		question: 'What does the public site commit to on data residency today?',
		answer:
			'Current public materials do not commit to a region-specific residency promise. Deployment-region and residency-specific requirements are handled through the enterprise review path.',
		status: 'enterprise'
	},
	{
		question: 'What can buyers review before a residency conversation?',
		answer:
			'Buyers can review the proof pack, technical docs, status page, pricing, and company/about materials before discussing environment-specific deployment requirements.',
		status: 'current'
	},
	{
		question: 'How are region-specific requests handled?',
		answer:
			'Region-specific hosting, residency constraints, and procurement conditions are handled as scoped diligence items in the enterprise validation lane.',
		status: 'enterprise'
	}
]);

export const PUBLIC_REVIEW_CHANNELS = Object.freeze([
	{
		label: 'Proof Pack',
		href: '/proof',
		note: 'Access posture, approval controls, decision-history integrity, and validation scope.'
	},
	{
		label: 'Docs',
		href: '/docs',
		note: 'Technical validation, onboarding, owner routing, and export-ready operating guidance.'
	},
	{
		label: 'Enterprise Path',
		href: '/enterprise',
		note: 'Formal diligence lane for procurement, architecture review, and rollout governance.'
	},
	{
		label: 'Talk to Sales',
		href: '/talk-to-sales',
		note: 'Human routing for rollout, security, pricing-fit, and regional evaluation questions.'
	}
]);
