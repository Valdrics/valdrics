export type DashboardAction = {
	href: string;
	label: string;
	variant: 'primary' | 'secondary';
};

export type DashboardPersonaContent = {
	title: string;
	subtitle: string;
	nextActionsCopy: string;
	actions: DashboardAction[];
};

export const PUBLIC_HOME_META = {
	title: 'Valdrics | Turn Spend Signals into Governed Action',
	description:
		'Valdrics turns cloud, SaaS, and software spend signals into owner-routed approvals, workflow execution, remediation, and exportable proof.',
	keywords:
		'spend governance platform, cloud cost governance, SaaS spend management, software spend governance, FinOps platform, ITAM optimization, governed remediation',
	ogDescription:
		'Turn cloud, SaaS, and software spend signals into owner-routed approvals, workflow execution, and exportable proof.'
} as const;

export function getDashboardPersonaContent(persona: string): DashboardPersonaContent {
	switch (persona) {
		case 'finance':
			return {
				title: 'Finance',
				subtitle: 'Allocation coverage, unit economics, and spend drivers.',
				nextActionsCopy: 'Review allocation coverage, unit economics anomalies, and savings proof.',
				actions: [
					{ href: '/leaderboards', label: 'Leaderboards', variant: 'secondary' },
					{ href: '/savings', label: 'Savings Proof', variant: 'primary' }
				]
			};
		case 'platform':
			return {
				title: 'Platform',
				subtitle: 'Reliability, guardrails, and connector health.',
				nextActionsCopy: 'Check job reliability, policy guardrails, and connector health.',
				actions: [
					{ href: '/ops', label: 'Ops Center', variant: 'primary' },
					{ href: '/settings', label: 'Guardrails', variant: 'secondary' }
				]
			};
		case 'leadership':
			return {
				title: 'Leadership',
				subtitle: 'Top drivers, carbon, and savings proof.',
				nextActionsCopy: 'Validate savings impact and monitor high-level cost drivers.',
				actions: [
					{ href: '/savings', label: 'Savings Proof', variant: 'primary' },
					{ href: '/leaderboards', label: 'Leaderboards', variant: 'secondary' }
				]
			};
		case 'engineering':
		default:
			return {
				title: 'Engineering',
				subtitle: 'Waste signals, findings, and safe remediation.',
				nextActionsCopy: 'Triage findings and run policy-previewed remediation safely.',
				actions: [
					{ href: '/ops', label: 'Review Findings', variant: 'primary' },
					{ href: '/connections', label: 'Add Connection', variant: 'secondary' }
				]
			};
	}
}
