import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import Page from './+page.svelte';

vi.mock('$app/paths', () => ({
	base: '',
	assets: ''
}));

vi.mock('$app/stores', () => ({
	page: readable({ url: new URL('https://example.com/enterprise') })
}));

describe('enterprise page', () => {
	it('renders enterprise governance narrative with dual-track actions', () => {
		render(Page);

		expect(screen.getByRole('heading', { level: 1 })).toBeTruthy();
		expect(
			screen.getByRole('heading', { name: /enterprise-critical control pillars/i })
		).toBeTruthy();
		expect(
			screen.getByRole('heading', { name: /formal diligence and procurement workflows/i })
		).toBeTruthy();

		const briefingLink = screen.getByRole('link', { name: /request enterprise briefing/i });
		expect(briefingLink.getAttribute('href')).toBe(
			'/talk-to-sales?intent=enterprise_briefing&entry=enterprise'
		);

		expect(screen.getByRole('link', { name: /talk to sales/i }).getAttribute('href')).toBe(
			'/talk-to-sales'
		);
		expect(screen.getByRole('link', { name: /view plans/i }).getAttribute('href')).toBe('/pricing');
		expect(
			screen.getByRole('link', { name: /download executive one-pager/i }).getAttribute('href')
		).toBe('/resources/valdrics-enterprise-one-pager.md');
		expect(
			screen.getByRole('link', { name: /download compliance checklist/i }).getAttribute('href')
		).toBe('/resources/global-finops-compliance-workbook.md');
		expect(
			screen.getByRole('link', { name: /enterprise@valdrics\.com/i }).getAttribute('href')
		).toContain('mailto:enterprise@valdrics.com');
	});
});
