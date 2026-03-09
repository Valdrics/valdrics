import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import Page from './+page.svelte';

vi.mock('$app/paths', () => ({
	base: '',
	assets: ''
}));

vi.mock('$app/stores', () => ({
	page: readable({ url: new URL('https://example.com/resources') })
}));

describe('resources page contact directory', () => {
	it('shows extended public contact channels outside the landing footer', () => {
		render(Page);

		expect(screen.getByRole('heading', { name: /contact directory/i })).toBeTruthy();
		expect(screen.getAllByRole('link', { name: /open resource/i })[0]?.getAttribute('href')).toBe(
			'/resources/enterprise-governance-overview'
		);
		expect(screen.getByRole('link', { name: /enterprise@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /sales@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /support@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /security@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /billing@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /privacy@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /hello@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /abuse@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /postmaster@valdrics\.com/i })).toBeTruthy();
	});
});
