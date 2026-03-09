import { afterEach, describe, expect, it, vi } from 'vitest';
import { POST } from './+server';

vi.mock('$lib/server/backend-origin', () => ({
	resolveBackendOrigin: () => 'https://api.example.com'
}));

function buildRequest(body: unknown, headers?: HeadersInit): Request {
	return new Request('https://example.com/api/marketing/talk-to-sales', {
		method: 'POST',
		headers: { 'content-type': 'application/json', ...headers },
		body: JSON.stringify(body)
	});
}

function buildEvent(overrides: Record<string, unknown>): Parameters<typeof POST>[0] {
	return {
		request: buildRequest({}),
		fetch: vi.fn(),
		...overrides
	} as unknown as Parameters<typeof POST>[0];
}

afterEach(() => {
	vi.restoreAllMocks();
});

describe('talk-to-sales proxy route', () => {
	it('accepts valid inquiry payloads and forwards turnstile tokens', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(
				JSON.stringify({ ok: true, accepted: true, inquiryId: 'inquiry-1', emailHash: 'a'.repeat(64) }),
				{
					status: 202,
					headers: { 'content-type': 'application/json' }
				}
			)
		);
		const response = await POST({
			...buildEvent({
				request: buildRequest(
					{
						name: 'Buyer One',
						email: 'buyer@example.com',
						company: 'Example Inc',
						timeline: 'this_quarter',
						interestArea: 'security_review'
					},
					{ 'x-turnstile-token': 'turnstile-token' }
				),
				fetch: fetchMock
			})
		});

		expect(response.status).toBe(202);
		const payload = await response.json();
		expect(payload.ok).toBe(true);
		expect(payload.inquiryId).toBe('inquiry-1');
		expect(fetchMock).toHaveBeenCalledOnce();
		const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
		expect(init.headers).toMatchObject({
			'content-type': 'application/json',
			'x-turnstile-token': 'turnstile-token'
		});
	});

	it('rejects invalid inquiry payloads', async () => {
		const response = await POST(
			buildEvent({
				request: buildRequest({ email: 'buyer@example.com', company: 'Example Inc' })
			})
		);

		expect(response.status).toBe(400);
		const payload = await response.json();
		expect(payload.ok).toBe(false);
		expect(payload.error).toBe('invalid_payload');
	});

	it('silently accepts honeypot submissions', async () => {
		const fetchMock = vi.fn();
		const response = await POST(
			buildEvent({
				request: buildRequest({
					name: 'Bot',
					email: 'bot@example.com',
					company: 'Bots Inc',
					honey: 'filled'
				}),
				fetch: fetchMock
			})
		);

		expect(response.status).toBe(202);
		const payload = await response.json();
		expect(payload.ok).toBe(true);
		expect(payload.accepted).toBe(true);
		expect(fetchMock).not.toHaveBeenCalled();
	});

	it('maps backend validation failures to invalid payload', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(JSON.stringify({ detail: 'invalid' }), {
				status: 422,
				headers: { 'content-type': 'application/json' }
			})
		);
		const response = await POST(
			buildEvent({
				request: buildRequest({
					name: 'Buyer One',
					email: 'buyer@example.com',
					company: 'Example Inc'
				}),
				fetch: fetchMock
			})
		);

		expect(response.status).toBe(400);
		const payload = await response.json();
		expect(payload.error).toBe('invalid_payload');
	});

	it('returns delivery failure when upstream submission fails', async () => {
		const response = await POST(
			buildEvent({
				request: buildRequest({
					name: 'Buyer One',
					email: 'buyer@example.com',
					company: 'Example Inc'
				}),
				fetch: vi.fn().mockRejectedValue(new Error('upstream unavailable'))
			})
		);

		expect(response.status).toBe(503);
		const payload = await response.json();
		expect(payload.ok).toBe(false);
		expect(payload.error).toBe('delivery_failed');
	});
});
