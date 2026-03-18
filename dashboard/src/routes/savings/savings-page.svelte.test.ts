import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import { getUpgradePrompt } from '$lib/pricing/upgradePrompt';
import Page from './+page.svelte';
import type { PageData } from './$types';

const { getMock } = vi.hoisted(() => ({
	getMock: vi.fn()
}));

vi.mock('$env/static/public', () => ({
	PUBLIC_API_URL: 'https://api.test/api/v1'
}));

vi.mock('$env/dynamic/public', () => ({
	env: {
		PUBLIC_API_URL: 'https://api.test/api/v1'
	}
}));

vi.mock('$app/paths', () => ({
	base: ''
}));

vi.mock('$lib/api', () => ({
	api: {
		get: (...args: unknown[]) => getMock(...args)
	}
}));

function jsonResponse(payload: unknown, status = 200): Response {
	return new Response(JSON.stringify(payload), {
		status,
		headers: { 'Content-Type': 'application/json' }
	});
}

describe('savings proof page', () => {
	afterEach(() => {
		cleanup();
		getMock.mockReset();
	});

	it('renders savings proof breakdown from API', async () => {
		getMock.mockImplementation(async (url: string) => {
			if (url.includes('/savings/proof/drilldown')) {
				return jsonResponse({
					start_date: '2026-02-01',
					end_date: '2026-02-10',
					as_of: '2026-02-13T00:00:00Z',
					tier: 'pro',
					provider: null,
					dimension: 'strategy_type',
					opportunity_monthly_usd: 123.45,
					realized_monthly_usd: 67.89,
					buckets: [
						{
							key: 'reserved_instance',
							opportunity_monthly_usd: 100.0,
							realized_monthly_usd: 50.0,
							open_recommendations: 2,
							applied_recommendations: 1,
							pending_remediations: 0,
							completed_remediations: 0
						}
					],
					truncated: false,
					limit: 50,
					notes: ['Grouped by strategy type.']
				});
			}
			if (url.includes('/savings/realized/events')) {
				return jsonResponse([
					{
						remediation_request_id: 'req-1',
						finding_id: 'finding-1',
						finding_category: 'idle_instances',
						provider: 'aws',
						account_id: 'acct-1',
						resource_id: 'i-123',
						region: 'us-east-1',
						method: 'ledger_delta_avg_daily_v1',
						executed_at: '2026-02-12T10:00:00Z',
						baseline_start_date: '2026-02-01',
						baseline_end_date: '2026-02-07',
						measurement_start_date: '2026-02-08',
						measurement_end_date: '2026-02-14',
						baseline_avg_daily_cost_usd: 10,
						measurement_avg_daily_cost_usd: 5,
						realized_monthly_savings_usd: 150,
						confidence_score: 0.9,
						computed_at: '2026-02-15T00:00:00Z'
					}
				]);
			}
			return jsonResponse({
				start_date: '2026-02-01',
				end_date: '2026-02-10',
				as_of: '2026-02-13T00:00:00Z',
				tier: 'pro',
				opportunity_monthly_usd: 123.45,
				realized_monthly_usd: 67.89,
				open_recommendations: 3,
				applied_recommendations: 1,
				pending_remediations: 2,
				completed_remediations: 1,
				breakdown: [
					{
						provider: 'aws',
						opportunity_monthly_usd: 100.0,
						realized_monthly_usd: 50.0,
						open_recommendations: 2,
						applied_recommendations: 1,
						pending_remediations: 1,
						completed_remediations: 1
					}
				],
				notes: ['Opportunity is a snapshot.']
			});
		});

		const data = {
			user: { id: 'user-id' },
			session: { access_token: 'token' },
			subscription: { tier: 'pro', status: 'active' }
		} as unknown as PageData;

		render(Page, { data });

		await screen.findByText('Breakdown');
		expect(
			screen.getByText('Completed remediations with finance-grade realized savings evidence')
		).toBeTruthy();
		expect(screen.getByText('idle_instances')).toBeTruthy();
		expect(screen.getByText('i-123')).toBeTruthy();

		await waitFor(() => {
			expect(getMock).toHaveBeenCalled();
		});
	});

	it('supports finding category drilldown', async () => {
		getMock.mockImplementation(async (url: string) => {
			if (url.includes('/savings/proof/drilldown')) {
				const params = new URL(url, 'https://app.test').searchParams;
				return jsonResponse({
					start_date: '2026-02-01',
					end_date: '2026-02-10',
					as_of: '2026-02-13T00:00:00Z',
					tier: 'pro',
					provider: null,
					dimension: params.get('dimension') || 'strategy_type',
					opportunity_monthly_usd: 12,
					realized_monthly_usd: 20,
					buckets: [
						{
							key: 'idle_instances',
							opportunity_monthly_usd: 4,
							realized_monthly_usd: 20,
							open_recommendations: 0,
							applied_recommendations: 0,
							pending_remediations: 1,
							completed_remediations: 1
						}
					],
					truncated: false,
					limit: 50,
					notes: ['Finding category grouped output.']
				});
			}
			if (url.includes('/savings/realized/events')) {
				return jsonResponse([]);
			}
			return jsonResponse({
				start_date: '2026-02-01',
				end_date: '2026-02-10',
				as_of: '2026-02-13T00:00:00Z',
				tier: 'pro',
				opportunity_monthly_usd: 12,
				realized_monthly_usd: 20,
				open_recommendations: 0,
				applied_recommendations: 0,
				pending_remediations: 1,
				completed_remediations: 1,
				breakdown: [],
				notes: []
			});
		});

		const data = {
			user: { id: 'user-id' },
			session: { access_token: 'token' },
			subscription: { tier: 'pro', status: 'active' }
		} as unknown as PageData;

		render(Page, { data });
		await screen.findByText('Drilldown');
		const select = await screen.findByLabelText('Drilldown dimension');
		await waitFor(() => {
			expect(select).toBeTruthy();
		});
		(select as HTMLSelectElement).value = 'finding_category';
		select.dispatchEvent(new Event('change'));

		await screen.findByText('idle_instances');
	});

	it('shows pro plan prompt for non-pro tiers without loading report data', async () => {
		const upgradePrompt = getUpgradePrompt('pro', 'savings proof');
		const data = {
			user: { id: 'user-id' },
			session: { access_token: 'token' },
			subscription: { tier: 'growth', status: 'active' }
		} as unknown as PageData;

		render(Page, { data });

		expect(screen.getByText(upgradePrompt.heading)).toBeTruthy();
		expect(screen.getByText(upgradePrompt.body)).toBeTruthy();
		expect(screen.getByRole('link', { name: upgradePrompt.cta })).toBeTruthy();
		await waitFor(() => {
			expect(getMock).not.toHaveBeenCalled();
		});
	});
});
