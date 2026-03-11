import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { getPublicContentEntry } from '$lib/content/publicContent';
import PublicContentArticlePage from './PublicContentArticlePage.svelte';

vi.mock('$app/paths', () => ({
	base: '',
	assets: ''
}));

vi.mock('$app/stores', () => ({
	page: readable({ url: new URL('https://example.com/docs/quick-start-workspace') })
}));

describe('PublicContentArticlePage', () => {
	afterEach(() => {
		cleanup();
		document.head.innerHTML = '';
	});

	it('renders structured content, related links, and article metadata', () => {
		const entry = getPublicContentEntry('docs', 'quick-start-workspace');
		expect(entry).toBeTruthy();
		if (!entry) return;

		render(PublicContentArticlePage, {
			entry,
			hubHref: '/docs',
			hubLabel: 'Back to Documentation'
		});

		expect(
			screen.getByRole('heading', { level: 1, name: /quick start a valdrics workspace/i })
		).toBeTruthy();
		const primaryHref = screen
			.getByRole('link', { name: /start free workspace/i })
			.getAttribute('href');
		expect(primaryHref || '').toContain('/auth/login?');
		expect(primaryHref || '').toContain('entry=docs_quick_start_workspace');
		expect(primaryHref || '').toContain('source=docs_quick_start_workspace_primary');
		const hubHref = screen
			.getByRole('link', { name: /back to documentation/i })
			.getAttribute('href');
		expect(hubHref || '').toContain('/docs?');
		expect(hubHref || '').toContain('source=docs_quick_start_workspace_hub');
		expect(screen.getByRole('heading', { name: /related content/i })).toBeTruthy();

		expect(document.head.innerHTML).toContain('og:type');
		expect(document.head.innerHTML).toContain('article:published_time');
		expect(document.head.innerHTML).toContain('application/ld+json');
		expect(document.head.innerHTML).toContain('TechArticle');
	});
});
