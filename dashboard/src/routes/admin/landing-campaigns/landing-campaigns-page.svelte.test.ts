import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/svelte';

import Page from './+page.svelte';
import type { PageData } from './$types';

const { fetchWithTimeoutMock } = vi.hoisted(() => ({
	fetchWithTimeoutMock: vi.fn()
}));

vi.mock('$lib/fetchWithTimeout', () => ({
	TimeoutError: class TimeoutError extends Error {},
	fetchWithTimeout: (...args: unknown[]) => fetchWithTimeoutMock(...args)
}));

vi.mock('$lib/edgeProxy', () => ({
	edgeApiPath: (path: string) => `/api/edge/api/v1${path}`
}));

function jsonResponse(payload: unknown, status = 200): Response {
	return new Response(JSON.stringify(payload), {
		status,
		headers: { 'Content-Type': 'application/json' }
	});
}

describe('landing campaign analytics page', () => {
	beforeEach(() => {
		fetchWithTimeoutMock.mockReset();
		fetchWithTimeoutMock.mockResolvedValue(
			jsonResponse({
				window_start: '2026-03-01',
				window_end: '2026-03-30',
				days: 30,
				total_events: 25,
				total_onboarded_tenants: 4,
				total_connected_tenants: 3,
				total_first_value_tenants: 2,
				total_pql_tenants: 2,
				total_pricing_view_tenants: 2,
				total_checkout_started_tenants: 1,
				total_paid_tenants: 1,
				weekly_current: {
					total_events: 12,
					cta_events: 5,
					signup_intent_events: 3,
					onboarded_tenants: 3,
					connected_tenants: 2,
					first_value_tenants: 1,
					pql_tenants: 1,
					pricing_view_tenants: 1,
					checkout_started_tenants: 1,
					paid_tenants: 1,
					signup_to_connection_rate: 2 / 3,
					connection_to_first_value_rate: 0.5
				},
				weekly_previous: {
					total_events: 9,
					cta_events: 4,
					signup_intent_events: 2,
					onboarded_tenants: 2,
					connected_tenants: 2,
					first_value_tenants: 2,
					pql_tenants: 2,
					pricing_view_tenants: 1,
					checkout_started_tenants: 0,
					paid_tenants: 0,
					signup_to_connection_rate: 1,
					connection_to_first_value_rate: 1
				},
				weekly_delta: {
					total_events: 3,
					signup_intent_events: 1,
					onboarded_tenants: 1,
					connected_tenants: 0,
					first_value_tenants: -1,
					pql_tenants: -1,
					pricing_view_tenants: 0,
					checkout_started_tenants: 1,
					paid_tenants: 1,
					signup_to_connection_rate: -1 / 3,
					connection_to_first_value_rate: -0.5
				},
				funnel_alerts: [
					{
						key: 'signup_to_connection',
						label: 'Signup -> connection',
						status: 'watch',
						threshold_rate: 0.35,
						current_rate: 2 / 3,
						previous_rate: 1,
						weekly_delta: -1 / 3,
						current_numerator: 2,
						current_denominator: 3,
						message: 'Conversion stayed above floor but deteriorated sharply versus the prior week.'
					},
					{
						key: 'connection_to_first_value',
						label: 'Connection -> first value',
						status: 'watch',
						threshold_rate: 0.4,
						current_rate: 0.5,
						previous_rate: 1,
						weekly_delta: -0.5,
						current_numerator: 1,
						current_denominator: 2,
						message: 'Conversion stayed above floor but deteriorated sharply versus the prior week.'
					}
				],
				items: [
					{
						utm_source: 'google',
						utm_medium: 'cpc',
						utm_campaign: 'launch',
						total_events: 25,
						cta_events: 10,
						signup_intent_events: 4,
						onboarded_tenants: 4,
						connected_tenants: 3,
						first_value_tenants: 2,
						pql_tenants: 2,
						pricing_view_tenants: 2,
						checkout_started_tenants: 1,
						paid_tenants: 1,
						first_seen_at: '2026-03-10T10:00:00.000Z',
						last_seen_at: '2026-03-10T11:00:00.000Z'
					}
				]
			})
		);
	});

	afterEach(() => {
		cleanup();
	});

	it('renders anonymous-to-paid campaign metrics for authenticated admins', async () => {
		render(Page, {
			props: {
				data: {
					user: { id: 'admin-user' },
					session: { access_token: 'token' }
				} as unknown as PageData
			}
		});

		await screen.findByRole('heading', { name: /landing campaign analytics/i });
		await waitFor(() => {
			expect(fetchWithTimeoutMock).toHaveBeenCalledTimes(1);
			expect(screen.queryByText(/loading campaign analytics/i)).toBeNull();
		});

		expect(screen.getByText(/authenticated activation and paid conversion/i)).toBeTruthy();
		expect(screen.getAllByText(/^Paid activations$/i).length).toBeGreaterThan(0);
		expect(screen.getAllByText(/^Onboarded$/i).length).toBeGreaterThan(0);
		expect(screen.getAllByText(/^Connected$/i).length).toBeGreaterThan(0);
		expect(screen.getAllByText(/^First value$/i).length).toBeGreaterThan(0);
		expect(screen.getAllByText(/^Checkout started$/i).length).toBeGreaterThan(0);
		expect(screen.getByText('launch')).toBeTruthy();
		expect(screen.getByText('google')).toBeTruthy();
		expect(screen.getByText('cpc')).toBeTruthy();
		expect(screen.getByText('2026-03-01 to 2026-03-30')).toBeTruthy();
		expect(screen.getByText(/2 product-qualified tenants/i)).toBeTruthy();
		expect(screen.getByText(/weekly funnel health alerts/i)).toBeTruthy();
		expect(screen.getByText(/7d signup → connection/i)).toBeTruthy();
		expect(screen.getByText(/threshold 35.0%/i)).toBeTruthy();
		expect(screen.getByText(/current 1 vs previous 2/i)).toBeTruthy();
	});
});
