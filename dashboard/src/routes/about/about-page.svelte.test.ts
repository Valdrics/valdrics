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
	it('renders a public company, founder surface, and review channels', () => {
		render(Page);

		expect(
			screen.getByRole('heading', {
				level: 1,
				name: /meet the team behind valdrics/i
			})
		).toBeTruthy();
		expect(
			screen.getByRole('link', { name: /start free workspace/i }).getAttribute('href') || ''
		).toContain('/auth/login?');
		expect(
			screen.getAllByRole('link', { name: /open proof pack/i })[0]?.getAttribute('href') || ''
		).toContain('/proof?');
		expect(screen.getByText(/abdulgoniyy dare/i)).toBeTruthy();
		expect(
			screen.getByText(
				/valdrics supports buyer evaluations across multiple regions\. deployment, residency, and procurement requirements that vary by region move through the enterprise review path\./i
			)
		).toBeTruthy();
		expect(screen.getByText(/deployment claims stay factual/i)).toBeTruthy();
		expect(screen.getAllByRole('link', { name: /open enterprise path/i }).length).toBeGreaterThan(
			0
		);
		expect(screen.getByRole('link', { name: /legal@valdrics\.com/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /security@valdrics\.com/i })).toBeTruthy();
	});
});
