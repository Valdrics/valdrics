import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import Page from './+page.svelte';

vi.mock('$app/paths', () => ({
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
		const legalMailLink = screen.getByRole('link', { name: /hello@valdrics.com/i });
		expect(legalMailLink.getAttribute('href')).toBe('mailto:hello@valdrics.com');
		const billingMailLink = screen.getByRole('link', { name: /billing@valdrics.com/i });
		expect(billingMailLink.getAttribute('href')).toBe('mailto:billing@valdrics.com');
	});
});
