import { describe, expect, it } from 'vitest';

import {
	getPublicContentEntry,
	listPublicContent,
	listPublicSitemapEntries,
	listRelatedPublicContent
} from './publicContent';

describe('public content registry', () => {
	it('exposes typed content collections for each public kind', () => {
		expect(listPublicContent('docs').length).toBeGreaterThan(0);
		expect(listPublicContent('resources').length).toBeGreaterThan(0);
		expect(listPublicContent('insights').length).toBeGreaterThan(0);
		expect(listPublicContent('proof').length).toBeGreaterThan(0);
	});

	it('resolves related entries without dangling references', () => {
		const entry = getPublicContentEntry('insights', 'from-alert-to-approved-action');
		expect(entry).toBeTruthy();
		if (!entry) {
			return;
		}

		const related = listRelatedPublicContent(entry);
		expect(related.map((item) => `${item.kind}:${item.slug}`)).toEqual([
			'docs:owner-routing-and-approval-path',
			'proof:identity-and-approval-controls'
		]);
	});

	it('produces sitemap entries for all public slug pages', () => {
		const sitemapEntries = listPublicSitemapEntries();

		expect(sitemapEntries.some((entry) => entry.path === '/insights/from-alert-to-approved-action')).toBe(
			true
		);
		expect(sitemapEntries.some((entry) => entry.path === '/proof/safe-access-model')).toBe(true);
		expect(sitemapEntries.some((entry) => entry.path === '/resources/executive-one-pager')).toBe(
			true
		);
		expect(sitemapEntries.some((entry) => entry.path === '/docs/quick-start-workspace')).toBe(true);
	});
});
