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

		expect(
			screen.getByRole('heading', { level: 1, name: /enterprise review that stays clear/i })
		).toBeTruthy();
		expect(
			screen.getByRole('heading', {
				name: /give legal, security, and procurement teams a coherent next step/i
			})
		).toBeTruthy();
		expect(
			screen.getByRole('heading', { name: /choose the path that matches the buying process/i })
		).toBeTruthy();
		expect(
			screen.getByRole('heading', { name: /open the first materials buyers usually ask for/i })
		).toBeTruthy();

		const briefingLink = screen.getAllByRole('link', { name: /request enterprise briefing/i })[0];
		expect(briefingLink).toBeTruthy();
		expect(briefingLink.getAttribute('href') || '').toContain('/talk-to-sales?');
		expect(briefingLink.getAttribute('href') || '').toContain('entry=enterprise');
		expect(briefingLink.getAttribute('href') || '').toContain('source=enterprise_lane');
		expect(briefingLink.getAttribute('href') || '').toContain('intent=enterprise_briefing');

		expect(
			screen.getByRole('link', { name: /start free workspace/i }).getAttribute('href') || ''
		).toContain('/auth/login?');
		expect(
			screen.getAllByRole('link', { name: /view pricing/i })[0]?.getAttribute('href') || ''
		).toContain('/pricing?');
		expect(screen.getByRole('link', { name: /executive one-pager/i }).getAttribute('href')).toBe(
			'/resources/valdrics-enterprise-one-pager.md'
		);
		expect(screen.getByRole('link', { name: /compliance checklist/i }).getAttribute('href')).toBe(
			'/resources/global-finops-compliance-workbook.md'
		);
		const proofLinks = screen.getAllByRole('link', { name: /open proof pack/i });
		expect(proofLinks.length).toBeGreaterThanOrEqual(1);
		for (const proofLink of proofLinks) {
			expect(proofLink.getAttribute('href') || '').toContain('/proof?');
		}
		expect(
			screen.getByRole('link', { name: /review privacy posture/i }).getAttribute('href') || ''
		).toContain('/privacy?');
		expect(
			screen.getByRole('link', { name: /review terms/i }).getAttribute('href') || ''
		).toContain('/terms?');
		expect(
			screen.getByRole('link', { name: /enterprise@valdrics\.com/i }).getAttribute('href')
		).toContain('mailto:enterprise@valdrics.com');
	});
});
