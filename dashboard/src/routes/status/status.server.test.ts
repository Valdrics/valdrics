import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
	fetchWithTimeout: vi.fn(),
	resolveBackendOrigin: vi.fn(() => 'https://api.valdrics.test')
}));

vi.mock('$lib/fetchWithTimeout', async () => {
	const actual =
		await vi.importActual<typeof import('$lib/fetchWithTimeout')>('$lib/fetchWithTimeout');
	return {
		...actual,
		fetchWithTimeout: mocks.fetchWithTimeout
	};
});

vi.mock('$lib/server/backend-origin', () => ({
	resolveBackendOrigin: mocks.resolveBackendOrigin
}));

import { load } from './+page.server';
import type { StatusSnapshot } from './statusPage';

function jsonResponse(payload: unknown, status = 200): Response {
	return new Response(JSON.stringify(payload), {
		status,
		headers: { 'Content-Type': 'application/json' }
	});
}

describe('status server load', () => {
	beforeEach(() => {
		mocks.fetchWithTimeout.mockReset();
		mocks.resolveBackendOrigin.mockClear();
	});

	it('returns a live snapshot when the backend health payload is valid', async () => {
		const setHeaders = vi.fn();
		mocks.fetchWithTimeout.mockResolvedValueOnce(
			jsonResponse({
				status: 'healthy',
				timestamp: '2026-03-09T10:00:00Z',
				database: { status: 'up' },
				redis: { status: 'healthy' },
				aws: { status: 'healthy', response_code: 403 },
				system: { status: 'healthy' },
				checks: {
					background_jobs: { status: 'healthy' },
					external_services: { status: 'healthy', services: { aws_sts: { status: 'healthy' } } }
				}
			})
		);

		const result = (await load({
			fetch: vi.fn() as unknown as typeof fetch,
			setHeaders
		} as unknown as Parameters<typeof load>[0])) as StatusSnapshot;

		expect(mocks.resolveBackendOrigin).toHaveBeenCalledTimes(1);
		expect(mocks.fetchWithTimeout).toHaveBeenCalledTimes(1);
		expect(setHeaders).toHaveBeenCalledWith({ 'Cache-Control': 'no-store' });
		expect(result.source).toBe('live');
		expect(result.summaryLabel).toBe('Operational');
		expect(result.components.some((component) => component.name === 'Database')).toBe(true);
	});

	it('uses the backend health payload even when the endpoint returns 503', async () => {
		const setHeaders = vi.fn();
		mocks.fetchWithTimeout.mockResolvedValueOnce(
			jsonResponse(
				{
					status: 'unhealthy',
					timestamp: '2026-03-09T11:00:00Z',
					database: { status: 'down', error: 'database unavailable' },
					redis: { status: 'healthy' },
					aws: { status: 'healthy' },
					system: { status: 'healthy' },
					checks: {
						background_jobs: { status: 'healthy' }
					}
				},
				503
			)
		);

		const result = (await load({
			fetch: vi.fn() as unknown as typeof fetch,
			setHeaders
		} as unknown as Parameters<typeof load>[0])) as StatusSnapshot;

		expect(result.source).toBe('live');
		expect(result.summaryLabel).toBe('Incident detected');
		expect(result.components.find((component) => component.name === 'Database')?.statusLabel).toBe(
			'Unavailable'
		);
	});

	it('falls back cleanly when the health fetch fails', async () => {
		const setHeaders = vi.fn();
		mocks.resolveBackendOrigin.mockReturnValueOnce('https://api.valdrics.test');
		mocks.fetchWithTimeout.mockRejectedValueOnce(new Error('network down'));

		const result = (await load({
			fetch: vi.fn() as unknown as typeof fetch,
			setHeaders
		} as unknown as Parameters<typeof load>[0])) as StatusSnapshot;

		expect(result.source).toBe('fallback');
		expect(result.summaryLabel).toBe('Status unavailable');
		expect(result.summaryDetail).toMatch(/temporarily unavailable/i);
	});

	it('surfaces a local-backend hint when localhost health is unreachable', async () => {
		const setHeaders = vi.fn();
		mocks.resolveBackendOrigin.mockReturnValueOnce('http://localhost:8000');
		mocks.fetchWithTimeout.mockRejectedValueOnce(new Error('connection refused'));

		const result = (await load({
			fetch: vi.fn() as unknown as typeof fetch,
			setHeaders
		} as unknown as Parameters<typeof load>[0])) as StatusSnapshot;

		expect(result.source).toBe('fallback');
		expect(result.summaryDetail).toContain('http://localhost:8000');
		expect(result.summaryDetail).toMatch(/start the backend/i);
	});
});
