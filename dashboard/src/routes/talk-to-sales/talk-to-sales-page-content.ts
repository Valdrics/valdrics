export type SalesInquiryForm = {
	name: string;
	email: string;
	company: string;
	role: string;
	teamSize: string;
	deploymentScope: string;
	timeline: string;
	interestArea: string;
	message: string;
	honey: string;
};

export const salesMailHref =
	'mailto:enterprise@valdrics.com?cc=sales@valdrics.com&subject=Valdrics%20Enterprise%20Briefing&body=Team%20size%3A%0ACloud%2FSaaS%20scope%3A%0ATarget%20timeline%3A';

export const heroHighlights = [
	{
		label: 'Buyer-safe path',
		value: 'Security, rollout effort, and commercial fit handled in one conversation'
	},
	{
		label: 'Fast response',
		value: 'Most qualified inquiries receive a human reply within one business day'
	},
	{
		label: 'No forced lane',
		value: 'We can route you to free, self-serve, or enterprise without restarting the process'
	}
] as const;

export const responseChecklist = [
	'Recommend the right plan lane: Free, Starter, Growth, Pro, or enterprise',
	'Map rollout effort and first-workflow timing',
	'Answer security, approval, and evidence questions with the right artifacts'
] as const;

export const sidebarCards = [
	{
		kicker: 'What to prepare',
		title: 'Bring the real buying context',
		copy: 'Cloud and SaaS scope, owner team, approval expectations, and target timing help us route you faster.'
	},
	{
		kicker: 'Best for',
		title: 'Security and procurement reviews',
		copy: 'Use this path when SSO/SCIM, diligence artifacts, or formal rollout controls need their own track.'
	},
	{
		kicker: 'Fallback',
		title: 'Prefer direct email?',
		copy: 'You can still reach us directly if your procurement or mail security flow blocks web forms.'
	}
] as const;

export const teamSizeOptions = [
	{ value: '', label: 'Select team size' },
	{ value: '1-5', label: '1-5 people' },
	{ value: '6-20', label: '6-20 people' },
	{ value: '21-50', label: '21-50 people' },
	{ value: '51-200', label: '51-200 people' },
	{ value: '201-1000', label: '201-1000 people' },
	{ value: '1000+', label: '1000+ people' }
] as const;

export const timelineOptions = [
	{ value: '', label: 'Select target timeline' },
	{ value: 'this_month', label: 'This month' },
	{ value: 'this_quarter', label: 'This quarter' },
	{ value: 'next_quarter', label: 'Next quarter' },
	{ value: 'evaluating', label: 'Still evaluating' }
] as const;

export const interestAreaOptions = [
	{ value: '', label: 'Choose primary interest area' },
	{ value: 'plan_fit', label: 'Plan fit' },
	{ value: 'security_review', label: 'Security review' },
	{ value: 'procurement', label: 'Procurement / commercial review' },
	{ value: 'multi_cloud', label: 'Multi-cloud control coverage' },
	{ value: 'greenops', label: 'GreenOps / carbon governance' },
	{ value: 'saas_governance', label: 'SaaS / license governance' },
	{ value: 'executive_briefing', label: 'Executive briefing' }
] as const;

export function createInitialSalesInquiryForm(): SalesInquiryForm {
	return {
		name: '',
		email: '',
		company: '',
		role: '',
		teamSize: '',
		deploymentScope: '',
		timeline: '',
		interestArea: '',
		message: '',
		honey: ''
	};
}

export function normalizeOptionalField(value: string): string | undefined {
	const text = value.trim();
	return text.length > 0 ? text : undefined;
}

export function resolveSalesInquirySource(currentUrl: URL | null): string | undefined {
	if (!currentUrl) return 'talk_to_sales_page';
	return (
		currentUrl.searchParams.get('source') ||
		currentUrl.searchParams.get('entry') ||
		(currentUrl.searchParams.get('intent')
			? `intent:${currentUrl.searchParams.get('intent')}`
			: '') ||
		'talk_to_sales_page'
	);
}

export function mapSalesInquiryError(errorCode: string | undefined): string {
	switch (errorCode) {
		case 'invalid_payload':
			return 'Check the required fields and try again.';
		case 'turnstile_verification_failed':
		case 'turnstile_verification_unavailable':
			return 'Verification failed. Retry in a moment or use the direct email fallback.';
		case 'delivery_failed':
		default:
			return 'We could not route the inquiry right now. Use the direct email fallback if this persists.';
	}
}
