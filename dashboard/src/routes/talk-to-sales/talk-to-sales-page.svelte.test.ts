import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import Page from './+page.svelte';

vi.mock('$app/paths', () => ({
	base: ''
}));

describe('talk-to-sales page', () => {
	it('renders enterprise sales paths and CTAs', () => {
		render(Page);

		expect(screen.getByRole('heading', { level: 1, name: /talk to sales/i })).toBeTruthy();
		expect(
			screen.getByRole('heading', { name: /starter\/growth\/pro onboarding and rollout/i })
		).toBeTruthy();
		expect(screen.getByRole('heading', { name: /security and governance review/i })).toBeTruthy();
		expect(
			screen.getByRole('heading', { name: /commercial and procurement diligence/i })
		).toBeTruthy();

			const emailSalesLinks = screen.getAllByRole('link', { name: /email sales/i });
			expect(emailSalesLinks[0]?.getAttribute('href') || '').toContain(
				'mailto:enterprise@valdrics.com'
			);
			expect(emailSalesLinks[0]?.getAttribute('href') || '').toContain('cc=sales@valdrics.com');

		const resourcesLink = screen.getByRole('link', { name: /open sales resources/i });
		expect(resourcesLink.getAttribute('href')).toBe('/resources');

		const enterpriseOverviewLink = screen.getAllByRole('link', {
			name: /explore enterprise overview/i
		})[0];
		expect(enterpriseOverviewLink?.getAttribute('href')).toBe('/enterprise');

		const startFreeLink = screen.getAllByRole('link', { name: /start free instead/i })[0];
		expect(startFreeLink?.getAttribute('href')).toContain('/auth/login?intent=talk_to_sales');
	});
});
