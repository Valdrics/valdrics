/**
 * Server Hooks - Runs on every request
 *
 * Purpose:
 * 1. Creates Supabase client for server-side use
 * 2. Validates and refreshes sessions
 * 3. Makes session available to routes via locals
 */

import { createServerClient } from '@supabase/ssr';
import { env as publicEnv } from '$env/dynamic/public';
import { env } from '$env/dynamic/private';
import type { Handle } from '@sveltejs/kit';
import type { Session, User } from '@supabase/supabase-js';
import { randomBytes, timingSafeEqual } from 'node:crypto';
import { serverLogger } from '$lib/logging/server';
import { isPublicPath } from '$lib/routeProtection';
import { canUseE2EAuthBypass, shouldUseSecureCookies } from '$lib/serverSecurity';
import {
	createPlaywrightE2EAccessToken,
	decodePlaywrightE2EBrowserSessionCookie,
	resolvePlaywrightSupabaseStorageKey,
	resolvePlaywrightE2EFixture,
	verifyPlaywrightE2EAccessToken
} from '$lib/testing/playwrightE2EAuth';

const E2E_AUTH_HEADER = 'x-valdrics-e2e-auth';

function buildE2EBypassAuth(params: {
	jwtSecret: string;
	jwtIssuer: string;
	fixture: ReturnType<typeof resolvePlaywrightE2EFixture>;
}): { session: Session; user: User } {
	const now = Math.floor(Date.now() / 1000);
	const accessToken = createPlaywrightE2EAccessToken({
		secret: params.jwtSecret,
		issuer: params.jwtIssuer,
		fixture: params.fixture
	});
	const user = {
		id: params.fixture.userId,
		aud: 'authenticated',
		role: 'authenticated',
		email: params.fixture.email,
		email_confirmed_at: new Date(0).toISOString(),
		phone: '',
		app_metadata: { provider: 'email', providers: ['email'] },
		user_metadata: { name: params.fixture.userName, source: 'playwright' },
		identities: [],
		created_at: new Date(0).toISOString(),
		updated_at: new Date().toISOString(),
		is_anonymous: false
	} as unknown as User;

	const session = {
		access_token: accessToken,
		refresh_token: randomBytes(32).toString('hex'),
		expires_in: 3600,
		expires_at: now + 3600,
		token_type: 'bearer',
		user
	} as unknown as Session;

	return { session, user };
}

function hasMatchingE2ESecret(provided: string | null, expected: string): boolean {
	const providedValue = String(provided || '').trim();
	const expectedValue = String(expected || '').trim();
	if (!providedValue || !expectedValue) {
		return false;
	}

	const providedBytes = Buffer.from(providedValue, 'utf8');
	const expectedBytes = Buffer.from(expectedValue, 'utf8');
	if (providedBytes.length !== expectedBytes.length) {
		return false;
	}

	return timingSafeEqual(providedBytes, expectedBytes);
}

function resolveE2EFixtureFromEnv() {
	return resolvePlaywrightE2EFixture({
		tenantId: env.PLAYWRIGHT_E2E_TENANT_ID,
		tenantName: env.PLAYWRIGHT_E2E_TENANT_NAME,
		userId: env.PLAYWRIGHT_E2E_USER_ID,
		userName: env.PLAYWRIGHT_E2E_USER_NAME,
		email: env.PLAYWRIGHT_E2E_USER_EMAIL,
		role: env.PLAYWRIGHT_E2E_USER_ROLE,
		persona: env.PLAYWRIGHT_E2E_USER_PERSONA,
		tier: env.PLAYWRIGHT_E2E_TIER
	});
}

function tryResolveE2ECookieSession(params: {
	event: Parameters<Handle>[0]['event'];
	publicSupabaseUrl: string;
	jwtSecret: string;
	jwtIssuer: string;
	fixture: ReturnType<typeof resolvePlaywrightE2EFixture>;
}): { session: Session; user: User } | null {
	const storageKey =
		String(env.PLAYWRIGHT_SUPABASE_STORAGE_KEY || '').trim() ||
		resolvePlaywrightSupabaseStorageKey(params.publicSupabaseUrl);
	if (!storageKey) {
		return null;
	}

	const browserSession = decodePlaywrightE2EBrowserSessionCookie(
		params.event.cookies.get(storageKey)
	);
	if (!browserSession) {
		return null;
	}

	if (
		browserSession.user.id !== params.fixture.userId ||
		browserSession.user.email !== params.fixture.email ||
		!verifyPlaywrightE2EAccessToken({
			token: browserSession.access_token,
			secret: params.jwtSecret,
			issuer: params.jwtIssuer,
			fixture: params.fixture
		})
	) {
		serverLogger.warn('e2e_auth_cookie_validation_failed', {
			url: params.event.url.toString(),
			storageKey
		});
		return null;
	}

	return buildE2EBypassAuth({
		jwtSecret: params.jwtSecret,
		jwtIssuer: params.jwtIssuer,
		fixture: params.fixture
	});
}

export const handle: Handle = async ({ event, resolve }) => {
	const isPublic = isPublicPath(event.url.pathname);
	const isHttps = shouldUseSecureCookies(event.url, env.NODE_ENV || '');
	const publicSupabaseUrl = String(publicEnv.PUBLIC_SUPABASE_URL || '').trim();
	const publicSupabaseAnonKey = String(publicEnv.PUBLIC_SUPABASE_ANON_KEY || '').trim();
	const hasSupabasePublicConfig = !!(publicSupabaseUrl && publicSupabaseAnonKey);

	if (hasSupabasePublicConfig) {
		// Create a Supabase client with cookie handling
		event.locals.supabase = createServerClient(publicSupabaseUrl, publicSupabaseAnonKey, {
			cookies: {
				get: (key) => event.cookies.get(key),
				set: (key, value, options) => {
					event.cookies.set(key, value, {
						path: '/',
						httpOnly: true,
						secure: isHttps,
						sameSite: 'strict',
						...options
					});
				},
				remove: (key, options) => {
					event.cookies.delete(key, {
						path: '/',
						httpOnly: true,
						secure: isHttps,
						sameSite: 'strict',
						...options
					});
				}
			}
		});
	}

	event.locals.safeGetSession = async () => {
		if (!hasSupabasePublicConfig) {
			return { session: null, user: null };
		}

		const testingMode = env.TESTING === 'true';
		const allowProdPreviewBypass = env.E2E_ALLOW_PROD_PREVIEW === 'true';
		const canUseBypass = canUseE2EAuthBypass({
			testingMode,
			allowProdPreviewBypass,
			isDevBuild: import.meta.env.DEV,
			hostname: event.url.hostname
		});
		if (canUseBypass) {
			const fixture = resolveE2EFixtureFromEnv();
			const jwtSecret = String(env.SUPABASE_JWT_SECRET || '').trim();
			const jwtIssuer = String(env.SUPABASE_JWT_ISSUER || 'supabase').trim() || 'supabase';
			const provided = event.request.headers.get(E2E_AUTH_HEADER);
			const expected = String(env.E2E_AUTH_SECRET || '').trim();
			if (hasMatchingE2ESecret(provided, expected)) {
				try {
					return buildE2EBypassAuth({
						jwtSecret,
						jwtIssuer,
						fixture
					});
				} catch (error) {
					serverLogger.error('e2e_auth_bypass_session_build_failed', {
						url: event.url.toString(),
						error: error instanceof Error ? error.message : String(error)
					});
					return { session: null, user: null };
				}
			}

			const cookieSession = tryResolveE2ECookieSession({
				event,
				publicSupabaseUrl,
				jwtSecret,
				jwtIssuer,
				fixture
			});
			if (cookieSession) {
				return cookieSession;
			}
		}

		try {
			const {
				data: { session }
			} = await event.locals.supabase.auth.getSession();
			if (!session) return { session: null, user: null };

			const {
				data: { user },
				error
			} = await event.locals.supabase.auth.getUser();

			if (error || !user) {
				serverLogger.warn('supabase_session_validation_failed', {
					url: event.url.toString(),
					hasError: !!error,
					error: error?.message ?? null
				});
				return { session: null, user: null };
			}

			return { session, user };
		} catch (error) {
			serverLogger.error('supabase_session_resolution_failed', {
				url: event.url.toString(),
				error: error instanceof Error ? error.message : String(error)
			});
			return { session: null, user: null };
		}
	};

	// Auth Guard: Protect all application routes by default.
	// Only allow public access to explicit public paths (auth, pricing, landing, assets).
	if (!isPublic) {
		if (!hasSupabasePublicConfig) {
			return new Response('Service temporarily unavailable. Authentication is not configured.', {
				status: 503,
				headers: { 'Cache-Control': 'no-store' }
			});
		}
		const { session } = await event.locals.safeGetSession();
		if (!session) {
			return new Response(null, {
				status: 303,
				headers: { Location: '/auth/login' }
			});
		}
	}

	const response = await resolve(event, {
		// Filter out sensitive auth headers from responses
		filterSerializedResponseHeaders(name) {
			return name === 'content-range' || name === 'x-supabase-api-version';
		}
	});

	// Security: prevent intermediary caching of authenticated HTML responses.
	const contentType = response.headers.get('content-type') || '';
	if (contentType.startsWith('text/html') && !isPublic) {
		response.headers.set('Cache-Control', 'no-store');
	}

	// Baseline modern security headers (CSP is configured in `dashboard/svelte.config.js`).
	// Keep these conservative to avoid breaking embedded/auth flows.
	response.headers.set('X-Content-Type-Options', 'nosniff');
	response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
	response.headers.set('X-Frame-Options', 'DENY');
	response.headers.set(
		'Permissions-Policy',
		'camera=(), microphone=(), geolocation=(), payment=(), usb=()'
	);
	if (isHttps) {
		response.headers.set(
			'Strict-Transport-Security',
			'max-age=63072000; includeSubDomains; preload'
		);
	}

	return response;
};

/**
 * Global Error Handler - Catches unhandled errors during request processing
 */
export const handleError: import('@sveltejs/kit').HandleServerError = ({ error, event }) => {
	const errorId = crypto.randomUUID();

	serverLogger.error('Unhandled server error:', {
		errorId,
		error: error instanceof Error ? error.message : error,
		stack: error instanceof Error ? error.stack : undefined,
		url: event.url.toString()
	});

	return {
		message: 'An internal error occurred. Our engineering team has been notified.',
		errorId,
		code: 'INTERNAL_SERVER_ERROR'
	};
};
