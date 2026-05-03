import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';

import Page from './+page.svelte';
import type { PageData } from './$types';

const mocks = vi.hoisted(() => ({
	goto: vi.fn(),
	pageStore: {
		subscribe(run: (value: { url: URL }) => void) {
			run({ url: new URL('https://example.com/dashboard') });
			return () => {};
		}
	},
	trackProductFunnelStage: vi.fn()
}));

vi.mock('$app/paths', () => ({
	base: ''
}));

vi.mock('$app/navigation', () => ({
	goto: mocks.goto
}));

vi.mock('$app/stores', () => ({
	page: mocks.pageStore
}));

vi.mock('$lib/funnel/productFunnelTelemetry', () => ({
	trackProductFunnelStage: mocks.trackProductFunnelStage
}));

function createDashboardData(persona: 'engineering' | 'finance'): PageData {
	return {
		user: {
			id: 'user-1',
			tenant_id: 'tenant-1'
		},
		session: null,
		subscription: { tier: 'pro', status: 'active' },
		profile: { persona },
		costs: { total_cost: 1234.56 },
		carbon: persona === 'finance' ? { total_co2_kg: 42.4 } : null,
		zombies: {
			total_monthly_waste: 87.5,
			ai_analysis: null
		},
		analysis:
			persona === 'engineering'
				? { analysis: 'Review idle instances before the next deployment window.' }
				: null,
		allocation: persona === 'finance' ? { buckets: [] } : null,
		unitEconomics:
			persona === 'finance'
				? {
						threshold_percent: 20,
						anomaly_count: 1,
						metrics: [
							{
								metric_key: 'cost_per_request',
								label: 'Cost Per Request',
								cost_per_unit: 0.1,
								baseline_cost_per_unit: 0.08,
								delta_percent: 25,
								is_anomalous: true
							}
						]
					}
				: null,
		freshness: null,
		startDate: '2024-01-01',
		endDate: '2024-01-31',
		provider: '',
		error: ''
	} as unknown as PageData;
}

describe('dashboard page lazy sections', () => {
	beforeEach(() => {
		mocks.goto.mockReset();
		mocks.trackProductFunnelStage.mockReset();

		Object.defineProperty(window, 'matchMedia', {
			configurable: true,
			value: vi.fn().mockReturnValue({
				matches: false,
				addEventListener: vi.fn(),
				removeEventListener: vi.fn()
			})
		});

		vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
	});

	afterEach(() => {
		cleanup();
		vi.restoreAllMocks();
	});

	it('renders engineering insights after the lazy section resolves', async () => {
		render(Page, {
			data: createDashboardData('engineering')
		});

		expect(screen.getByText(/loading engineering insights/i)).toBeTruthy();

		await vi.dynamicImportSettled();
		await screen.findByRole('heading', { name: /ai insights/i });
		expect(
			screen.getByText(/review idle instances before the next deployment window/i)
		).toBeTruthy();
		await waitFor(() => {
			expect(screen.queryByText(/loading engineering insights/i)).toBeNull();
		});
	});

	it('renders finance insights after the lazy section resolves', async () => {
		render(Page, {
			data: createDashboardData('finance')
		});

		expect(screen.getByText(/loading finance insights/i)).toBeTruthy();

		await vi.dynamicImportSettled();
		await screen.findByText(/greenops sustainability/i);
		expect(screen.getByRole('heading', { name: /unit economics/i })).toBeTruthy();
		expect(await screen.findByRole('heading', { name: /12-month roa/i })).toBeTruthy();
		await waitFor(() => {
			expect(screen.queryByText(/loading finance insights/i)).toBeNull();
		});
	});

	it('offers AI in the dashboard spend provider selector', async () => {
		render(Page, {
			data: createDashboardData('finance')
		});

		const providerButton = await screen.findByRole('button', { name: /all providers/i });
		await fireEvent.click(providerButton);

		expect(await screen.findByRole('option', { name: /^AI$/i })).toBeTruthy();
	});
});
