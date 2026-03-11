import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import Page from './+page.svelte';

vi.mock('$app/paths', () => ({
	base: '',
	assets: ''
}));

vi.mock('$app/stores', () => ({
	page: readable({ url: new URL('https://example.com/about') })
}));

describe('about page', () => {
	it('renders a public company and review surface with direct contact channels', () => {
		render(Page);

		expect(
			screen.getByRole('heading', { level: 1, name: /a governed operating layer for spend decisions/i })
		).toBeTruthy();
		expect(
			screen.getByRole('link', { name: /start free workspace/i }).getAttribute('href') || ''
		).toContain('/auth/login?');
		expect(screen.getByRole('link', { name: /view pricing/i }).getAttribute('href') || '').toContain(
			'/pricing?'
		);
		const docsLinks = screen.getAllByRole('link', { name: /^open docs$/i });
		expect(docsLinks[0]?.getAttribute('href') || '').toContain('/docs?');
		expect(screen.getByText(/public proof is intentionally prelaunch-safe/i)).toBeTruthy();
		expect(screen.getByRole('link', { name: /licensing@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /legal@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /security@valdrics\.com/i })).toBeTruthy();
	});
});
