import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import Page from './+page.svelte';

vi.mock('$app/paths', () => ({
	base: '',
	assets: ''
}));

vi.mock('$app/stores', () => ({
	page: readable({ url: new URL('https://example.com/terms') })
}));

describe('terms page', () => {
	it('renders production service terms sections', () => {
		render(Page);

		expect(screen.getByRole('heading', { level: 1, name: /terms of service/i })).toBeTruthy();
		expect(screen.getByRole('heading', { name: /service scope/i })).toBeTruthy();
		expect(screen.getByRole('heading', { name: /billing and subscription/i })).toBeTruthy();
		expect(screen.getByRole('heading', { name: /limitation of liability/i })).toBeTruthy();
		expect(screen.getByRole('heading', { name: /governing law and disputes/i })).toBeTruthy();
		expect(
			screen.getByRole('heading', { name: /enterprise contracting and procurement path/i })
		).toBeTruthy();
		const legalMailLink = screen.getByRole('link', { name: /legal@valdrics.com/i });
		expect(legalMailLink.getAttribute('href')).toBe('mailto:legal@valdrics.com');
		const billingMailLink = screen.getByRole('link', { name: /billing@valdrics.com/i });
		expect(billingMailLink.getAttribute('href')).toBe('mailto:billing@valdrics.com');
		expect(screen.getByRole('link', { name: /open enterprise path/i }).getAttribute('href')).toBe(
			'/enterprise'
		);
		expect(screen.getByRole('link', { name: /view pricing/i }).getAttribute('href')).toBe(
			'/pricing'
		);
		expect(screen.getByRole('link', { name: /privacy and dpa path/i }).getAttribute('href')).toBe(
			'/privacy'
		);
		expect(screen.getByRole('link', { name: /talk to sales/i }).getAttribute('href')).toBe(
			'/talk-to-sales'
		);
	});
});
