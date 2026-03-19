import { beforeEach, describe, expect, it, vi } from 'vitest';
import { encodePlaywrightE2EBrowserSessionCookie } from '$lib/testing/playwrightE2EAuth';

const mocks = vi.hoisted(() => ({
	createServerClient: vi.fn(),
	canUseE2EAuthBypass: vi.fn(),
	shouldUseSecureCookies: vi.fn(),
	serverLogger: {
		error: vi.fn(),
		warn: vi.fn(),
		info: vi.fn()
	},
	publicEnv: {
		PUBLIC_SUPABASE_URL: 'https://supabase.example.co',
		PUBLIC_SUPABASE_ANON_KEY: 'anon-key'
	},
	privateEnv: {
		NODE_ENV: 'production',
		TESTING: 'false',
		E2E_ALLOW_PROD_PREVIEW: 'false',
		E2E_AUTH_SECRET: '',
		SUPABASE_JWT_SECRET: 'test-jwt-secret-at-least-32-bytes-long',
		SUPABASE_JWT_ISSUER: 'supabase',
		PLAYWRIGHT_SUPABASE_STORAGE_KEY: '',
		PLAYWRIGHT_E2E_USER_ID: '33333333-3333-4333-8333-333333333333',
		PLAYWRIGHT_E2E_USER_EMAIL: 'fixture@valdrics.test',
		PLAYWRIGHT_E2E_USER_NAME: 'Fixture User',
		PLAYWRIGHT_E2E_TENANT_ID: '11111111-1111-4111-8111-111111111111',
		PLAYWRIGHT_E2E_TENANT_NAME: 'Fixture Tenant',
		PLAYWRIGHT_E2E_USER_ROLE: 'admin',
		PLAYWRIGHT_E2E_USER_PERSONA: 'engineering',
		PLAYWRIGHT_E2E_TIER: 'growth'
	}
}));

vi.mock('@supabase/ssr', () => ({
	createServerClient: (...args: unknown[]) => mocks.createServerClient(...args)
}));

vi.mock('$env/dynamic/public', () => ({
	env: mocks.publicEnv
}));

vi.mock('$env/dynamic/private', () => ({
	env: mocks.privateEnv
}));

vi.mock('$lib/serverSecurity', () => ({
	canUseE2EAuthBypass: (...args: unknown[]) => mocks.canUseE2EAuthBypass(...args),
	shouldUseSecureCookies: (...args: unknown[]) => mocks.shouldUseSecureCookies(...args)
}));

vi.mock('$lib/logging/server', () => ({
	serverLogger: mocks.serverLogger
}));

import { handle } from './hooks.server';

function createEvent(
	url: string,
	headers: Record<string, string> = {}
): Parameters<typeof handle>[0]['event'] {
	return {
		request: new Request(url, { headers }),
		url: new URL(url),
		cookies: {
			get: vi.fn(),
			set: vi.fn(),
			delete: vi.fn()
		},
		locals: {}
	} as unknown as Parameters<typeof handle>[0]['event'];
}

describe('hooks.server handle', () => {
	beforeEach(() => {
		mocks.publicEnv.PUBLIC_SUPABASE_URL = 'https://supabase.example.co';
		mocks.publicEnv.PUBLIC_SUPABASE_ANON_KEY = 'anon-key';
		mocks.createServerClient.mockReset();
		mocks.canUseE2EAuthBypass.mockReset();
		mocks.shouldUseSecureCookies.mockReset();
		mocks.serverLogger.error.mockReset();
		mocks.serverLogger.warn.mockReset();
		mocks.serverLogger.info.mockReset();
		mocks.privateEnv.E2E_AUTH_SECRET = '';
		mocks.canUseE2EAuthBypass.mockReturnValue(false);
		mocks.shouldUseSecureCookies.mockReturnValue(true);
	});

	it('allows public routes even when Supabase public env is missing', async () => {
		mocks.publicEnv.PUBLIC_SUPABASE_URL = '';
		mocks.publicEnv.PUBLIC_SUPABASE_ANON_KEY = '';

		const event = createEvent('https://example.com/');
		const resolve = vi.fn(
			async () =>
				new Response('<html></html>', {
					status: 200,
					headers: { 'content-type': 'text/html' }
				})
		);

		const response = await handle({
			event,
			resolve
		} as Parameters<typeof handle>[0]);

		expect(response.status).toBe(200);
		expect(resolve).toHaveBeenCalledTimes(1);
		expect(mocks.createServerClient).not.toHaveBeenCalled();
		const sessionResult = await event.locals.safeGetSession();
		expect(sessionResult).toEqual({ session: null, user: null });
	});

	it('allows public helper APIs using the real public-path allowlist', async () => {
		mocks.publicEnv.PUBLIC_SUPABASE_URL = '';
		mocks.publicEnv.PUBLIC_SUPABASE_ANON_KEY = '';

		for (const url of [
			'https://example.com/api/geo/currency',
			'https://example.com/api/edge/health/live'
		]) {
			const event = createEvent(url);
			const resolve = vi.fn(
				async () =>
					new Response(JSON.stringify({ ok: true }), {
						status: 200,
						headers: { 'content-type': 'application/json' }
					})
			);

			const response = await handle({
				event,
				resolve
			} as Parameters<typeof handle>[0]);

			expect(response.status).toBe(200);
			expect(resolve).toHaveBeenCalledTimes(1);
		}
		expect(mocks.createServerClient).not.toHaveBeenCalled();
	});

	it('fails closed for protected routes when Supabase public env is missing', async () => {
		mocks.publicEnv.PUBLIC_SUPABASE_URL = '';
		mocks.publicEnv.PUBLIC_SUPABASE_ANON_KEY = '';

		const event = createEvent('https://example.com/ops');
		const resolve = vi.fn();

		const response = await handle({
			event,
			resolve
		} as Parameters<typeof handle>[0]);

		expect(response.status).toBe(503);
		expect(resolve).not.toHaveBeenCalled();
	});

	it('redirects protected routes to login when session is absent', async () => {
		mocks.createServerClient.mockReturnValue({
			auth: {
				getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
				getUser: vi.fn()
			}
		});

		const event = createEvent('https://example.com/settings');
		const resolve = vi.fn();

		const response = await handle({
			event,
			resolve
		} as Parameters<typeof handle>[0]);

		expect(response.status).toBe(303);
		expect(response.headers.get('location')).toBe('/auth/login');
		expect(resolve).not.toHaveBeenCalled();
	});

	it('logs provider resolution faults and fails closed to null session', async () => {
		mocks.createServerClient.mockReturnValue({
			auth: {
				getSession: vi.fn().mockRejectedValue(new Error('dns failure')),
				getUser: vi.fn()
			}
		});

		const event = createEvent('https://example.com/');
		const resolve = vi.fn(
			async () =>
				new Response('<html></html>', {
					status: 200,
					headers: { 'content-type': 'text/html' }
				})
		);

		await handle({
			event,
			resolve
		} as Parameters<typeof handle>[0]);

		const sessionResult = await event.locals.safeGetSession();
		expect(sessionResult).toEqual({ session: null, user: null });
		expect(mocks.serverLogger.error).toHaveBeenCalledWith(
			'supabase_session_resolution_failed',
			expect.objectContaining({ error: 'dns failure' })
		);
	});

	it('uses constant-time bypass matching and builds non-static e2e sessions', async () => {
		mocks.canUseE2EAuthBypass.mockReturnValue(true);
		mocks.privateEnv.E2E_AUTH_SECRET = 'test-shared-secret';
		mocks.createServerClient.mockReturnValue({
			auth: {
				getSession: vi.fn(),
				getUser: vi.fn()
			}
		});

		const event = createEvent('https://example.com/', {
			'x-valdrics-e2e-auth': 'test-shared-secret'
		});
		const resolve = vi.fn(
			async () =>
				new Response('<html></html>', {
					status: 200,
					headers: { 'content-type': 'text/html' }
				})
		);

		await handle({
			event,
			resolve
		} as Parameters<typeof handle>[0]);

		const sessionResult = await event.locals.safeGetSession();
		expect(sessionResult.user?.id).toBe(mocks.privateEnv.PLAYWRIGHT_E2E_USER_ID);
		expect(sessionResult.user?.email).toBe(mocks.privateEnv.PLAYWRIGHT_E2E_USER_EMAIL);
		expect(sessionResult.session?.access_token.split('.')).toHaveLength(3);
		expect(sessionResult.session?.refresh_token).toMatch(/^[0-9a-f]{64}$/i);
	});

	it('accepts a seeded browser session cookie during guarded e2e bypass mode', async () => {
		mocks.canUseE2EAuthBypass.mockReturnValue(true);
		mocks.privateEnv.PLAYWRIGHT_SUPABASE_STORAGE_KEY = 'sb-test-auth-token';
		mocks.createServerClient.mockReturnValue({
			auth: {
				getSession: vi.fn(),
				getUser: vi.fn()
			}
		});

		const event = createEvent('https://example.com/dashboard');
		const cookieValue = encodePlaywrightE2EBrowserSessionCookie({
			secret: mocks.privateEnv.SUPABASE_JWT_SECRET,
			issuer: mocks.privateEnv.SUPABASE_JWT_ISSUER,
			fixture: {
				tenantId: mocks.privateEnv.PLAYWRIGHT_E2E_TENANT_ID,
				tenantName: mocks.privateEnv.PLAYWRIGHT_E2E_TENANT_NAME,
				userId: mocks.privateEnv.PLAYWRIGHT_E2E_USER_ID,
				userName: mocks.privateEnv.PLAYWRIGHT_E2E_USER_NAME,
				email: mocks.privateEnv.PLAYWRIGHT_E2E_USER_EMAIL,
				role: mocks.privateEnv.PLAYWRIGHT_E2E_USER_ROLE,
				persona: mocks.privateEnv.PLAYWRIGHT_E2E_USER_PERSONA,
				tier: mocks.privateEnv.PLAYWRIGHT_E2E_TIER
			}
		});
		vi.mocked(event.cookies.get).mockImplementation((key: string) =>
			key === 'sb-test-auth-token' ? cookieValue : undefined
		);

		const resolve = vi.fn(
			async () =>
				new Response('<html></html>', {
					status: 200,
					headers: { 'content-type': 'text/html' }
				})
		);

		await handle({
			event,
			resolve
		} as Parameters<typeof handle>[0]);

		const sessionResult = await event.locals.safeGetSession();
		expect(sessionResult.user?.email).toBe(mocks.privateEnv.PLAYWRIGHT_E2E_USER_EMAIL);
		expect(sessionResult.session?.access_token.split('.')).toHaveLength(3);
	});
});
