import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import Page from './+page.svelte';

vi.mock('$app/paths', () => ({
	base: ''
}));

describe('docs page', () => {
	it('renders core documentation sections and links', () => {
		render(Page);

		const heading = screen.getByRole('heading', { level: 1, name: /documentation/i });
		expect(heading).toBeTruthy();

			const quickStartLink = screen.getByRole('link', { name: /start free workspace/i });
			expect(quickStartLink.getAttribute('href')).toContain('/auth/login?mode=signup');

			const apiLinks = screen.getAllByRole('link', { name: /open api docs/i });
			expect(apiLinks[0]?.getAttribute('href')).toBe('/docs/api');

			const validationLinks = screen.getAllByRole('link', { name: /open technical validation/i });
			expect(validationLinks[0]?.getAttribute('href')).toBe('/docs/technical-validation');

		const resourcesLink = screen.getByRole('link', { name: /open resources/i });
		expect(resourcesLink.getAttribute('href')).toBe('/resources');
		const insightsLink = screen.getByRole('link', { name: /open insights/i });
		expect(insightsLink.getAttribute('href')).toBe('/insights');

		const pricingLinks = screen.getAllByRole('link', { name: /view pricing/i });
		expect(pricingLinks[0]?.getAttribute('href')).toBe('/pricing');

		const repoLink = screen.getByRole('link', { name: /browse github docs/i });
		expect(repoLink.getAttribute('href')).toBe(
			'https://github.com/Valdrics-AI/valdrics/tree/main/docs'
		);
	});
});
