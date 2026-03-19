import type { BrowserContext } from '@playwright/test';

import {
	createPlaywrightE2EAccessToken,
	encodePlaywrightE2EBrowserSessionCookie,
	resolvePlaywrightE2EFixture
} from '../../src/lib/testing/playwrightE2EAuth';

export const BASE_URL = process.env.DASHBOARD_URL || 'http://localhost:4173';
export const BACKEND_URL = process.env.PLAYWRIGHT_BACKEND_URL || 'http://127.0.0.1:8000';
export const E2E_AUTH_HEADER_NAME = 'x-valdrics-e2e-auth';
export const E2E_AUTH_HEADER_VALUE = process.env.E2E_AUTH_SECRET || 'playwright';
export const E2E_JWT_SECRET =
	process.env.SUPABASE_JWT_SECRET || 'test-jwt-secret-at-least-32-bytes-long';
export const E2E_JWT_ISSUER = process.env.SUPABASE_JWT_ISSUER || 'supabase';
export const E2E_FIXTURE = resolvePlaywrightE2EFixture();
const E2E_BROWSER_SESSION_LIFETIME_SECONDS = 12 * 60 * 60;
const PLAYWRIGHT_SUPABASE_STORAGE_KEY = String(
	process.env.PLAYWRIGHT_SUPABASE_STORAGE_KEY || ''
).trim();

type AuthenticatedSessionOptions = {
	browserSession?: boolean;
};

export function createFixtureAccessToken() {
	return createPlaywrightE2EAccessToken({
		secret: E2E_JWT_SECRET,
		issuer: E2E_JWT_ISSUER,
		fixture: E2E_FIXTURE
	});
}

export async function enableAuthenticatedSession(
	context: BrowserContext,
	options: AuthenticatedSessionOptions = {}
) {
	await context.setExtraHTTPHeaders({
		[E2E_AUTH_HEADER_NAME]: E2E_AUTH_HEADER_VALUE
	});

	if (!options.browserSession || !PLAYWRIGHT_SUPABASE_STORAGE_KEY) {
		return;
	}

	const origin = new URL(BASE_URL).origin;
	await context.addCookies([
		{
			name: PLAYWRIGHT_SUPABASE_STORAGE_KEY,
			value: encodePlaywrightE2EBrowserSessionCookie({
				secret: E2E_JWT_SECRET,
				issuer: E2E_JWT_ISSUER,
				fixture: E2E_FIXTURE,
				lifetimeSeconds: E2E_BROWSER_SESSION_LIFETIME_SECONDS
			}),
			url: origin,
			httpOnly: false,
			secure: origin.startsWith('https://'),
			sameSite: 'Lax'
		}
	]);
}
