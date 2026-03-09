import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
	fetchWithTimeout: vi.fn(),
	edgeApiPath: vi.fn((path: string) => `/api/edge/api/v1${path}`)
}));

vi.mock('$lib/fetchWithTimeout', () => ({
	fetchWithTimeout: mocks.fetchWithTimeout
}));

vi.mock('$lib/edgeProxy', () => ({
	edgeApiPath: mocks.edgeApiPath
}));

import { load } from './+page';
import { DEFAULT_PRICING_PLANS } from '../pricing/plans';
import type { BillingUsage } from './billingPage';
import type { PricingPlan } from '../pricing/plans';

type BillingLoadResult = {
	plans: PricingPlan[];
	usage: BillingUsage | null;
	checkoutSuccess: boolean;
};

function jsonResponse(payload: unknown, status = 200): Response {
	return new Response(JSON.stringify(payload), {
		status,
		headers: { 'Content-Type': 'application/json' }
	});
}

describe('billing page load', () => {
	beforeEach(() => {
		mocks.fetchWithTimeout.mockReset();
		mocks.edgeApiPath.mockClear();
	});

	it('falls back cleanly when no session is available', async () => {
		const result = (await load({
			fetch: vi.fn() as unknown as typeof fetch,
			parent: async () => ({
				session: null
			}),
			url: new URL('https://example.com/billing')
		} as Parameters<typeof load>[0])) as BillingLoadResult;

		expect(mocks.fetchWithTimeout).not.toHaveBeenCalled();
		expect(result.plans).toEqual(DEFAULT_PRICING_PLANS);
		expect(result.usage).toBeNull();
		expect(result.checkoutSuccess).toBe(false);
	});

	it('loads shared plans and usage for authenticated workspaces', async () => {
		const plans = [
			{
				id: 'starter',
				name: 'Starter',
				price_monthly: 49,
				price_annual: 490,
				period: '/mo',
				description: 'Starter',
				features: ['One provider scope'],
				cta: 'Start with Starter',
				popular: false
			}
		];
		const usage = {
			tier: 'starter',
			generated_at: '2026-03-09T10:00:00Z',
			connections: {
				aws: { connected: 1, limit: 3, remaining: 2, utilization_percent: 33.3 }
			}
		};

		mocks.fetchWithTimeout
			.mockResolvedValueOnce(jsonResponse(plans))
			.mockResolvedValueOnce(jsonResponse(usage));

		const result = (await load({
			fetch: vi.fn() as unknown as typeof fetch,
			parent: async () => ({
				session: { access_token: 'token' }
			}),
			url: new URL('https://example.com/billing?success=true')
		} as Parameters<typeof load>[0])) as BillingLoadResult;

		expect(mocks.fetchWithTimeout).toHaveBeenCalledTimes(2);
		expect(mocks.fetchWithTimeout.mock.calls[1]?.[2]).toEqual({
			headers: { Authorization: 'Bearer token' }
		});
		expect(result.plans).toEqual(plans);
		expect(result.usage).toEqual(usage);
		expect(result.checkoutSuccess).toBe(true);
	});

	it('keeps defaults when plans are invalid and usage fetch fails', async () => {
		mocks.fetchWithTimeout
			.mockResolvedValueOnce(jsonResponse([{ id: 'broken' }]))
			.mockResolvedValueOnce(new Response('bad gateway', { status: 502 }));

		const result = (await load({
			fetch: vi.fn() as unknown as typeof fetch,
			parent: async () => ({
				session: { access_token: 'token' }
			}),
			url: new URL('https://example.com/billing')
		} as Parameters<typeof load>[0])) as BillingLoadResult;

		expect(result.plans).toEqual(DEFAULT_PRICING_PLANS);
		expect(result.usage).toBeNull();
	});
});
