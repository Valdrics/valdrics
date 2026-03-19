import { createHmac } from 'node:crypto';
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
	DEFAULT_PLAYWRIGHT_E2E_FIXTURE,
	createPlaywrightE2EBrowserSession,
	createPlaywrightE2EAccessToken,
	decodePlaywrightE2EBrowserSessionCookie,
	encodePlaywrightE2EBrowserSessionCookie,
	resolvePlaywrightSupabaseStorageKey,
	resolvePlaywrightE2EFixture,
	verifyPlaywrightE2EAccessToken
} from './playwrightE2EAuth';

const ORIGINAL_ENV = { ...process.env };

function decodePayload(token: string): Record<string, unknown> {
	const payload = token.split('.')[1];
	if (!payload) {
		throw new Error('JWT payload segment is missing.');
	}
	return JSON.parse(Buffer.from(payload, 'base64url').toString('utf8')) as Record<string, unknown>;
}

describe('playwrightE2EAuth', () => {
	afterEach(() => {
		vi.unstubAllEnvs();
		process.env = { ...ORIGINAL_ENV };
	});

	it('resolves deterministic fixture defaults from environment overrides', () => {
		vi.stubEnv('PLAYWRIGHT_E2E_USER_EMAIL', 'auditor@valdrics.test');
		vi.stubEnv('PLAYWRIGHT_E2E_TIER', 'pro');

		expect(resolvePlaywrightE2EFixture()).toEqual({
			...DEFAULT_PLAYWRIGHT_E2E_FIXTURE,
			email: 'auditor@valdrics.test',
			tier: 'pro'
		});
	});

	it('creates a valid HS256 JWT for the seeded fixture user', () => {
		const token = createPlaywrightE2EAccessToken({
			secret: 'test-jwt-secret-at-least-32-bytes-long',
			fixture: DEFAULT_PLAYWRIGHT_E2E_FIXTURE,
			issuer: 'supabase',
			nowMs: Date.UTC(2026, 0, 1, 0, 0, 0),
			lifetimeSeconds: 900
		});

		const [header, payload, signature] = token.split('.');
		expect(header).toBeTruthy();
		expect(payload).toBeTruthy();
		expect(signature).toBeTruthy();

		const decoded = decodePayload(token);
		expect(decoded).toMatchObject({
			aud: 'authenticated',
			iss: 'supabase',
			sub: DEFAULT_PLAYWRIGHT_E2E_FIXTURE.userId,
			email: DEFAULT_PLAYWRIGHT_E2E_FIXTURE.email,
			role: 'authenticated',
			iat: 1767225600,
			exp: 1767226500
		});

		const expectedSignature = createHmac('sha256', 'test-jwt-secret-at-least-32-bytes-long')
			.update(`${header}.${payload}`)
			.digest('base64url');
		expect(signature).toBe(expectedSignature);
	});

	it('verifies fixture-backed access tokens', () => {
		const token = createPlaywrightE2EAccessToken({
			secret: 'test-jwt-secret-at-least-32-bytes-long',
			fixture: DEFAULT_PLAYWRIGHT_E2E_FIXTURE,
			nowMs: Date.UTC(2026, 0, 1, 0, 0, 0)
		});

		expect(
			verifyPlaywrightE2EAccessToken({
				token,
				secret: 'test-jwt-secret-at-least-32-bytes-long',
				fixture: DEFAULT_PLAYWRIGHT_E2E_FIXTURE,
				nowMs: Date.UTC(2026, 0, 1, 0, 30, 0)
			})
		).toBe(true);
		expect(
			verifyPlaywrightE2EAccessToken({
				token,
				secret: 'wrong-secret',
				fixture: DEFAULT_PLAYWRIGHT_E2E_FIXTURE,
				nowMs: Date.UTC(2026, 0, 1, 0, 30, 0)
			})
		).toBe(false);
	});

	it('encodes and decodes browser session cookies for seeded auth', () => {
		const cookieValue = encodePlaywrightE2EBrowserSessionCookie({
			secret: 'test-jwt-secret-at-least-32-bytes-long',
			fixture: DEFAULT_PLAYWRIGHT_E2E_FIXTURE,
			nowMs: Date.UTC(2026, 0, 1, 0, 0, 0)
		});

		const decoded = decodePlaywrightE2EBrowserSessionCookie(cookieValue);
		expect(decoded).toEqual(
			createPlaywrightE2EBrowserSession({
				secret: 'test-jwt-secret-at-least-32-bytes-long',
				fixture: DEFAULT_PLAYWRIGHT_E2E_FIXTURE,
				nowMs: Date.UTC(2026, 0, 1, 0, 0, 0)
			})
		);
	});

	it('derives the supabase browser storage key from the project ref', () => {
		expect(resolvePlaywrightSupabaseStorageKey('https://abc123.supabase.co')).toBe(
			'sb-abc123-auth-token'
		);
		expect(resolvePlaywrightSupabaseStorageKey('not-a-url')).toBe('');
	});
});
