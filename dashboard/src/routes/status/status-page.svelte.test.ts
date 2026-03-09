import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/svelte';

import Page from './+page.svelte';

describe('status page', () => {
	it('renders live service health cards', () => {
		render(Page, {
			data: {
				session: null,
				user: null,
				subscription: { tier: 'free', status: 'active' },
				profile: null,
				checkedAt: '2026-03-09T10:00:00Z',
				summaryLabel: 'Operational',
				summaryTone: 'success',
				summaryDetail: 'Core health checks are responding normally.',
				source: 'live',
				components: [
					{
						name: 'Platform API',
						statusLabel: 'Operational',
						tone: 'success',
						detail: 'Core health checks are responding normally.'
					},
					{
						name: 'Database',
						statusLabel: 'Operational',
						tone: 'success',
						detail: 'Primary database connectivity check passed.'
					}
				]
			}
		});

		expect(screen.getByRole('heading', { level: 1, name: /current platform status/i })).toBeTruthy();
		expect(screen.getByRole('heading', { level: 3, name: /platform api/i })).toBeTruthy();
		expect(screen.getByRole('heading', { level: 3, name: /database/i })).toBeTruthy();
		expect(screen.queryByText(/automated checks are unavailable/i)).toBeNull();
	});

	it('renders a fallback notice when the live summary is unavailable', () => {
		render(Page, {
			data: {
				session: null,
				user: null,
				subscription: { tier: 'free', status: 'active' },
				profile: null,
				checkedAt: '2026-03-09T10:00:00Z',
				summaryLabel: 'Status unavailable',
				summaryTone: 'neutral',
				summaryDetail: 'The automated health summary is temporarily unavailable.',
				source: 'fallback',
				components: [
					{
						name: 'Platform API',
						statusLabel: 'Unknown',
						tone: 'neutral',
						detail: 'The automated health summary is temporarily unavailable.'
					}
				]
			}
		});

		expect(screen.getByText(/automated checks are unavailable/i)).toBeTruthy();
		expect(screen.getByText(/status unavailable/i)).toBeTruthy();
	});
});
