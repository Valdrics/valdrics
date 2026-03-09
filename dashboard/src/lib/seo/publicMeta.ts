import type { PublicContentEntry } from '$lib/content/publicContent';

export type PublicStructuredDataPageType = 'CollectionPage' | 'WebPage' | 'ContactPage';

type StructuredData = Record<string, unknown>;

const SITE_NAME = 'Valdrics';

function organizationSchema(siteUrl: string): StructuredData {
	return {
		'@type': 'Organization',
		name: SITE_NAME,
		url: siteUrl
	};
}

function audienceSchemas(audiences: PublicContentEntry['audiences']): StructuredData[] {
	return audiences.map((audience) => ({
		'@type': 'Audience',
		audienceType: audience
	}));
}

export function resolveCanonicalUrl(url: URL): string {
	return new URL(url.pathname, url.origin).toString();
}

export function resolvePublicMetaImage(url: URL, assetsPath: string): string {
	return new URL(`${assetsPath}/og-image.png`, url.origin).toString();
}

export function buildPublicContentStructuredData(
	entry: PublicContentEntry,
	canonicalUrl: string
): StructuredData {
	const siteUrl = new URL('/', canonicalUrl).toString();
	const base = {
		'@context': 'https://schema.org',
		'@id': `${canonicalUrl}#primary`,
		url: canonicalUrl,
		name: entry.title,
		headline: entry.title,
		description: entry.seoDescription,
		dateModified: entry.updatedAt,
		datePublished: entry.updatedAt,
		mainEntityOfPage: canonicalUrl,
		publisher: organizationSchema(siteUrl),
		author: organizationSchema(siteUrl),
		audience: audienceSchemas(entry.audiences)
	} satisfies StructuredData;

	switch (entry.kind) {
		case 'docs':
			return {
				...base,
				'@type': 'TechArticle',
				articleSection: 'Documentation'
			};
		case 'insights':
			return {
				...base,
				'@type': 'BlogPosting',
				articleSection: 'Insights'
			};
		case 'resources':
			return {
				...base,
				'@type': 'CreativeWork'
			};
		case 'proof':
			return {
				...base,
				'@type': 'WebPage'
			};
	}
}

export function buildPublicPageStructuredData(input: {
	pageType: PublicStructuredDataPageType;
	name: string;
	description: string;
	canonicalUrl: string;
	section?: string;
	keywords?: string[];
}): StructuredData {
	const siteUrl = new URL('/', input.canonicalUrl).toString();
	return {
		'@context': 'https://schema.org',
		'@type': input.pageType,
		'@id': `${input.canonicalUrl}#primary`,
		url: input.canonicalUrl,
		name: input.name,
		description: input.description,
		isPartOf: {
			'@type': 'WebSite',
			name: SITE_NAME,
			url: siteUrl
		},
		publisher: organizationSchema(siteUrl),
		...(input.section ? { about: input.section } : {}),
		...(input.keywords && input.keywords.length > 0
			? { keywords: Array.from(new Set(input.keywords)).join(', ') }
			: {})
	};
}
