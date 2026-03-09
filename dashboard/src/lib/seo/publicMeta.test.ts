import { describe, expect, it } from 'vitest';
import { getPublicContentEntry } from '$lib/content/publicContent';
import {
	buildPublicContentStructuredData,
	buildPublicPageStructuredData,
	resolveCanonicalUrl,
	resolvePublicMetaImage
} from './publicMeta';

describe('public metadata helpers', () => {
	it('builds article structured data for docs content', () => {
		const entry = getPublicContentEntry('docs', 'quick-start-workspace');
		expect(entry).toBeTruthy();
		if (!entry) return;

		const jsonLd = buildPublicContentStructuredData(
			entry,
			'https://www.example.com/docs/quick-start-workspace'
		);

		expect(jsonLd['@type']).toBe('TechArticle');
		expect(jsonLd.headline).toBe('Quick Start a Valdrics Workspace');
		expect(jsonLd.dateModified).toBe(entry.updatedAt);
		expect(Array.isArray(jsonLd.audience)).toBe(true);
	});

	it('builds blog structured data for insight content', () => {
		const entry = getPublicContentEntry('insights', 'from-alert-to-approved-action');
		expect(entry).toBeTruthy();
		if (!entry) return;

		const jsonLd = buildPublicContentStructuredData(
			entry,
			'https://www.example.com/insights/from-alert-to-approved-action'
		);

		expect(jsonLd['@type']).toBe('BlogPosting');
		expect(jsonLd.articleSection).toBe('Insights');
		expect(jsonLd.mainEntityOfPage).toBe(
			'https://www.example.com/insights/from-alert-to-approved-action'
		);
	});

	it('builds public page structured data with stable keywords', () => {
		const jsonLd = buildPublicPageStructuredData({
			pageType: 'ContactPage',
			name: 'Talk to Sales',
			description: 'Start a real sales inquiry.',
			canonicalUrl: 'https://www.example.com/talk-to-sales',
			section: 'Sales',
			keywords: ['sales', 'enterprise', 'sales']
		});

		expect(jsonLd['@type']).toBe('ContactPage');
		expect(jsonLd.keywords).toBe('sales, enterprise');
		expect(jsonLd.about).toBe('Sales');
	});

	it('resolves canonical and og image URLs from route URLs', () => {
		const url = new URL('https://www.example.com/resources/executive-one-pager?utm_source=ads');
		expect(resolveCanonicalUrl(url)).toBe('https://www.example.com/resources/executive-one-pager');
		expect(resolvePublicMetaImage(url, '/_app/immutable/assets')).toBe(
			'https://www.example.com/_app/immutable/assets/og-image.png'
		);
	});
});
