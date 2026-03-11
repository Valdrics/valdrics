import { describe, expect, it, vi } from 'vitest';

import { captureLandingAttribution } from '$lib/landing/landingFunnel';
import type { StorageLike } from '$lib/landing/landingExperiment';

import {
	buildProductFunnelAttributionContext,
	buildProductFunnelPayload,
	trackProductFunnelStage
} from './productFunnelTelemetry';

class MemoryStorage implements StorageLike {
	private readonly store = new Map<string, string>();

	getItem(key: string): string | null {
		return this.store.get(key) ?? null;
	}

	setItem(key: string, value: string): void {
		this.store.set(key, value);
	}
}

describe('productFunnelTelemetry', () => {
	it('merges stored landing attribution with current URL utm overrides', () => {
		const storage = new MemoryStorage();
		captureLandingAttribution(
			new URL(
				'https://example.com/?utm_source=linkedin&utm_medium=paid_social&utm_campaign=retarget'
			),
			storage,
			new Date('2026-03-08T10:00:00.000Z')
		);

		const attribution = buildProductFunnelAttributionContext({
			url: new URL(
				'https://example.com/onboarding?utm_medium=cpc&utm_campaign=launch&intent=roi_assessment'
			),
			persona: 'Finance',
			storage
		});

		expect(attribution.persona).toBe('finance');
		expect(attribution.intent).toBe('roi_assessment');
		expect(attribution.page_path).toBe(
			'/onboarding?utm_medium=cpc&utm_campaign=launch&intent=roi_assessment'
		);
		expect(attribution.first_touch_at).toBe('2026-03-08T10:00:00.000Z');
		expect(attribution.utm?.source).toBe('linkedin');
		expect(attribution.utm?.medium).toBe('cpc');
		expect(attribution.utm?.campaign).toBe('launch');
	});

	it('builds a normalized product funnel payload', () => {
		const storage = new MemoryStorage();
		captureLandingAttribution(
			new URL('https://example.com/?utm_source=google&utm_medium=cpc&utm_campaign=launch'),
			storage,
			new Date('2026-03-08T10:00:00.000Z')
		);

		const payload = buildProductFunnelPayload({
			stage: 'connection_verified',
			url: new URL('https://example.com/onboarding?intent=roi_assessment'),
			currentTier: 'Growth',
			persona: 'Engineering',
			provider: 'AWS',
			source: 'Onboarding_Verify_Success',
			occurredAt: new Date('2026-03-09T12:30:00.000Z'),
			storage
		});

		expect(payload).toMatchObject({
			stage: 'connection_verified',
			provider: 'aws',
			source: 'onboarding_verify_success',
			current_tier: 'growth',
			occurred_at: '2026-03-09T12:30:00.000Z'
		});
		expect(payload.attribution?.persona).toBe('engineering');
		expect(payload.attribution?.utm?.source).toBe('google');
	});

	it('dedupes a stage only after a successful send', async () => {
		const storage = new MemoryStorage();
		const send = vi
			.fn<
				(
					url: string,
					body?: unknown,
					options?: { headers?: Record<string, string> }
				) => Promise<Response>
			>()
			.mockResolvedValue(new Response('{}', { status: 202 }));

		const input = {
			accessToken: 'token',
			stage: 'pricing_viewed' as const,
			tenantId: 'tenant-id',
			url: new URL('https://example.com/pricing'),
			currentTier: 'growth',
			storage,
			send
		};

		await expect(trackProductFunnelStage(input)).resolves.toBe(true);
		await expect(trackProductFunnelStage(input)).resolves.toBe(false);
		expect(send).toHaveBeenCalledTimes(1);
	});

	it('does not persist dedupe state when the send fails', async () => {
		const storage = new MemoryStorage();
		const send = vi
			.fn<
				(
					url: string,
					body?: unknown,
					options?: { headers?: Record<string, string> }
				) => Promise<Response>
			>()
			.mockResolvedValueOnce(new Response('{}', { status: 500 }))
			.mockResolvedValueOnce(new Response('{}', { status: 202 }));

		const input = {
			accessToken: 'token',
			stage: 'checkout_started' as const,
			tenantId: 'tenant-id',
			url: new URL('https://example.com/billing'),
			currentTier: 'pro',
			storage,
			send
		};

		await expect(trackProductFunnelStage(input)).resolves.toBe(false);
		await expect(trackProductFunnelStage(input)).resolves.toBe(true);
		expect(send).toHaveBeenCalledTimes(2);
	});
});
