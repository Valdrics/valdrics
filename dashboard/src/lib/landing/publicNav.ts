export interface PublicNavLink {
	href: string;
	label: string;
	external?: boolean;
}

export interface PublicNavLinkGroup {
	heading: string;
	links: readonly PublicNavLink[];
}

export interface PublicContactChannel {
	label: string;
	email: string;
	href: string;
}

export const PUBLIC_PRIMARY_LINKS: readonly PublicNavLink[] = Object.freeze([
	{ href: '/#product', label: 'Product' },
	{ href: '/pricing', label: 'Pricing' },
	{ href: '/enterprise', label: 'Enterprise' },
	{ href: '/resources', label: 'Resources' }
]);

export const PUBLIC_RESOURCES_DROPDOWN_LINKS: readonly PublicNavLink[] = Object.freeze([
	{ href: '/resources', label: 'Resource Hub' },
	{ href: '/about', label: 'About' },
	{ href: '/docs', label: 'Docs' },
	{ href: '/proof', label: 'Proof Pack' },
	{ href: '/insights', label: 'Insights' }
]);

export const PUBLIC_SECONDARY_LINKS: readonly PublicNavLink[] = Object.freeze([
	{ href: '/docs', label: 'Docs' },
	{ href: '/insights', label: 'Insights' },
	{ href: '/enterprise', label: 'Enterprise Review' }
]);

export const PUBLIC_MOBILE_LINKS: readonly PublicNavLink[] = Object.freeze([
	{ href: '/#product', label: 'Product' },
	{ href: '/pricing', label: 'Pricing' },
	{ href: '/enterprise', label: 'Enterprise' },
	{ href: '/resources', label: 'Resources' }
]);

export const PUBLIC_FOOTER_LINK_GROUPS: readonly PublicNavLinkGroup[] = Object.freeze([
	{
		heading: 'Product',
		links: Object.freeze([
			{ href: '/pricing', label: 'Pricing' },
			{ href: '/enterprise', label: 'Enterprise' },
			{ href: '/proof', label: 'Proof Pack' },
			{ href: '/docs', label: 'Documentation' }
		])
	},
	{
		heading: 'Company',
		links: Object.freeze([
			{ href: '/about', label: 'About' },
			{ href: '/talk-to-sales', label: 'Talk to Sales' },
			{ href: '/status', label: 'Status' }
		])
	},
	{
		heading: 'Legal',
		links: Object.freeze([
			{ href: '/privacy', label: 'Privacy' },
			{ href: '/terms', label: 'Terms' }
		])
	}
]);

export const PUBLIC_FOOTER_LINKS: readonly PublicNavLink[] = Object.freeze(
	PUBLIC_FOOTER_LINK_GROUPS.flatMap((group) => group.links)
);

export const PUBLIC_SIGNAL_STRIP: readonly string[] = Object.freeze([
	'Turn alerts into governed action',
	'Give every issue an owner',
	'Keep proof ready for leadership'
]);

export const PUBLIC_FOOTER_BADGES: readonly string[] = Object.freeze([
	'Spend governance',
	'Owner routing',
	'Approval trail',
	'Review-ready exports'
]);

export const PUBLIC_FOOTER_SUBTITLE =
	'Valdrics gives finance and engineering one operating layer for spend review, owner routing, approvals, and proof.';

export const PUBLIC_FOOTER_CAPTION =
	'Designed for teams that want clearer spend decisions, cleaner rollout, and review-ready proof.';

export const PUBLIC_CONTACT_CHANNELS: readonly PublicContactChannel[] = Object.freeze([
	{ label: 'Sales', email: 'sales@valdrics.com', href: 'mailto:sales@valdrics.com' },
	{ label: 'Support', email: 'support@valdrics.com', href: 'mailto:support@valdrics.com' },
	{ label: 'Security', email: 'security@valdrics.com', href: 'mailto:security@valdrics.com' }
]);

export const PUBLIC_EXTENDED_CONTACT_CHANNELS: readonly PublicContactChannel[] = Object.freeze([
	{ label: 'Enterprise', email: 'enterprise@valdrics.com', href: 'mailto:enterprise@valdrics.com' },
	{ label: 'Sales', email: 'sales@valdrics.com', href: 'mailto:sales@valdrics.com' },
	{ label: 'Support', email: 'support@valdrics.com', href: 'mailto:support@valdrics.com' },
	{ label: 'Security', email: 'security@valdrics.com', href: 'mailto:security@valdrics.com' },
	{ label: 'Licensing', email: 'licensing@valdrics.com', href: 'mailto:licensing@valdrics.com' },
	{ label: 'Legal', email: 'legal@valdrics.com', href: 'mailto:legal@valdrics.com' },
	{ label: 'Billing', email: 'billing@valdrics.com', href: 'mailto:billing@valdrics.com' },
	{ label: 'Privacy', email: 'privacy@valdrics.com', href: 'mailto:privacy@valdrics.com' },
	{ label: 'General', email: 'hello@valdrics.com', href: 'mailto:hello@valdrics.com' },
	{ label: 'Abuse', email: 'abuse@valdrics.com', href: 'mailto:abuse@valdrics.com' },
	{ label: 'Postmaster', email: 'postmaster@valdrics.com', href: 'mailto:postmaster@valdrics.com' }
]);
