import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import Page from './+page.svelte';
import { mustGetPublicContentEntry } from '$lib/content/publicContent';

vi.mock('$app/paths', () => ({
	base: '',
	assets: ''
}));

vi.mock('$app/stores', () => ({
	page: readable({ url: new URL('https://example.com/docs') })
}));

const SHARED_PAGE_DATA = {
	user: null,
	session: null,
	subscription: { tier: 'starter', status: 'active' },
	profile: null
} as const;

describe('docs page', () => {
	it('renders core documentation sections and links', () => {
		render(Page, {
			data: {
				...SHARED_PAGE_DATA,
				operatingGuides: [
					mustGetPublicContentEntry('docs', 'connect-first-provider'),
					mustGetPublicContentEntry('docs', 'owner-routing-and-approval-path'),
					mustGetPublicContentEntry('docs', 'decision-history-and-export-records')
				]
			}
		});

		const heading = screen.getByRole('heading', {
			level: 1,
			name: /documentation for setup, validation, and api review/i
		});
		expect(heading).toBeTruthy();

		const apiLinks = screen.getAllByRole('link', { name: /open api docs/i });
		expect(apiLinks[0]?.getAttribute('href')).toBe('/docs/api');

		const validationLinks = screen.getAllByRole('link', { name: /open technical validation/i });
		expect(validationLinks[0]?.getAttribute('href')).toBe('/docs/technical-validation');

		expect(screen.getByRole('heading', { name: /quick start a valdrics workspace/i })).toBeTruthy();
		expect(screen.getAllByRole('link', { name: /open guide/i })[0]?.getAttribute('href')).toBe(
			'/docs/quick-start-workspace'
		);
		expect(
			screen.getByRole('heading', { name: /use the core guides for the operating loop/i })
		).toBeTruthy();

		const repoLink = screen.getByRole('link', { name: /browse github docs/i });
		expect(repoLink.getAttribute('href')).toBe(
			'https://github.com/Valdrics/valdrics/tree/main/docs'
		);
	});
});
