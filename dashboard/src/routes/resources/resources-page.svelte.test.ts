import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import Page from './+page.svelte';
import { listPublicContent, mustGetPublicContentEntry } from '$lib/content/publicContent';

vi.mock('$app/paths', () => ({
	base: '',
	assets: ''
}));

vi.mock('$app/stores', () => ({
	page: readable({ url: new URL('https://example.com/resources') })
}));

const SHARED_PAGE_DATA = {
	user: null,
	session: null,
	subscription: { tier: 'starter', status: 'active' },
	profile: null
} as const;

describe('resources page contact directory', () => {
	it('shows extended public contact channels outside the landing footer', () => {
		render(Page, {
			data: {
				...SHARED_PAGE_DATA,
				resources: listPublicContent('resources'),
				guidedPaths: [
					{
						kicker: 'Internal alignment',
						title: 'Make the business case without a long deck rewrite',
						copy: 'Use concise assets when finance, leadership, or procurement needs the short version before the deeper review surfaces.',
						entries: [
							mustGetPublicContentEntry('resources', 'executive-one-pager'),
							mustGetPublicContentEntry('resources', 'roi-assumptions'),
							mustGetPublicContentEntry('resources', 'enterprise-governance-overview')
						]
					}
				],
				stageColumns: [
					{
						label: 'Learn',
						title: 'Run the first review with less noise',
						copy: 'Operational guides for teams that need a practical first loop.',
						entries: listPublicContent('resources').filter((resource) => resource.stage === 'learn')
					}
				]
			}
		});

		expect(
			screen.getByRole('heading', {
				level: 1,
				name: /resources for rollout, review, and diligence/i
			})
		).toBeTruthy();
		expect(
			screen.getByRole('link', { name: /start free workspace/i }).getAttribute('href') || ''
		).toContain('/auth/login?');
		expect(
			screen.getByRole('link', { name: /enterprise review/i }).getAttribute('href') || ''
		).toContain('/enterprise?');
		expect(screen.getByRole('heading', { name: /contact directory/i })).toBeTruthy();
		expect(
			screen
				.getAllByRole('link', { name: /enterprise governance overview/i })
				.some((link) => link.getAttribute('href') === '/resources/enterprise-governance-overview')
		).toBe(true);
		expect(screen.getByRole('link', { name: /enterprise@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /sales@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /support@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /security@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /licensing@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /legal@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /billing@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /privacy@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /hello@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /abuse@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /postmaster@valdrics\.com/i })).toBeTruthy();
	});
});
