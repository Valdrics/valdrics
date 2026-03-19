import { createHmac, timingSafeEqual } from 'node:crypto';

export interface PlaywrightE2EFixture {
	tenantId: string;
	tenantName: string;
	userId: string;
	userName: string;
	email: string;
	role: string;
	persona: string;
	tier: string;
}

export interface PlaywrightE2EBrowserSessionUser {
	id: string;
	aud: string;
	role: string;
	email: string;
	email_confirmed_at: string;
	phone: string;
	app_metadata: { provider: string; providers: string[] };
	user_metadata: { name: string; source: string };
	identities: unknown[];
	created_at: string;
	updated_at: string;
	is_anonymous: boolean;
}

export interface PlaywrightE2EBrowserSession {
	access_token: string;
	refresh_token: string;
	expires_in: number;
	expires_at: number;
	token_type: 'bearer';
	user: PlaywrightE2EBrowserSessionUser;
}

export const DEFAULT_PLAYWRIGHT_E2E_FIXTURE: PlaywrightE2EFixture = {
	tenantId: '11111111-1111-4111-8111-111111111111',
	tenantName: 'Playwright Test Tenant',
	userId: '22222222-2222-4222-8222-222222222222',
	userName: 'E2E Test User',
	email: 'e2e@valdrics.test',
	role: 'admin',
	persona: 'engineering',
	tier: 'growth'
};

function resolveValue(value: string | undefined, fallback: string): string {
	const normalized = String(value || '').trim();
	return normalized.length > 0 ? normalized : fallback;
}

export function resolvePlaywrightE2EFixture(
	values: Partial<Record<keyof PlaywrightE2EFixture, string | undefined>> = {}
): PlaywrightE2EFixture {
	return {
		tenantId: resolveValue(
			values.tenantId ?? process.env.PLAYWRIGHT_E2E_TENANT_ID,
			DEFAULT_PLAYWRIGHT_E2E_FIXTURE.tenantId
		),
		tenantName: resolveValue(
			values.tenantName ?? process.env.PLAYWRIGHT_E2E_TENANT_NAME,
			DEFAULT_PLAYWRIGHT_E2E_FIXTURE.tenantName
		),
		userId: resolveValue(
			values.userId ?? process.env.PLAYWRIGHT_E2E_USER_ID,
			DEFAULT_PLAYWRIGHT_E2E_FIXTURE.userId
		),
		userName: resolveValue(
			values.userName ?? process.env.PLAYWRIGHT_E2E_USER_NAME,
			DEFAULT_PLAYWRIGHT_E2E_FIXTURE.userName
		),
		email: resolveValue(
			values.email ?? process.env.PLAYWRIGHT_E2E_USER_EMAIL,
			DEFAULT_PLAYWRIGHT_E2E_FIXTURE.email
		),
		role: resolveValue(
			values.role ?? process.env.PLAYWRIGHT_E2E_USER_ROLE,
			DEFAULT_PLAYWRIGHT_E2E_FIXTURE.role
		),
		persona: resolveValue(
			values.persona ?? process.env.PLAYWRIGHT_E2E_USER_PERSONA,
			DEFAULT_PLAYWRIGHT_E2E_FIXTURE.persona
		),
		tier: resolveValue(
			values.tier ?? process.env.PLAYWRIGHT_E2E_TIER,
			DEFAULT_PLAYWRIGHT_E2E_FIXTURE.tier
		)
	};
}

function encodeSegment(value: Record<string, unknown>): string {
	return Buffer.from(JSON.stringify(value)).toString('base64url');
}

function decodeSegment(value: string): Record<string, unknown> {
	return JSON.parse(Buffer.from(value, 'base64url').toString('utf8')) as Record<string, unknown>;
}

function isTimingSafeEqual(left: string, right: string): boolean {
	const leftBytes = Buffer.from(left, 'utf8');
	const rightBytes = Buffer.from(right, 'utf8');
	if (leftBytes.length !== rightBytes.length) {
		return false;
	}
	return timingSafeEqual(leftBytes, rightBytes);
}

function isPlaywrightBrowserSession(value: unknown): value is PlaywrightE2EBrowserSession {
	if (typeof value !== 'object' || value === null) {
		return false;
	}

	const session = value as Partial<PlaywrightE2EBrowserSession>;
	return (
		typeof session.access_token === 'string' &&
		typeof session.refresh_token === 'string' &&
		typeof session.expires_in === 'number' &&
		typeof session.expires_at === 'number' &&
		session.token_type === 'bearer' &&
		typeof session.user === 'object' &&
		session.user !== null &&
		typeof session.user.id === 'string' &&
		typeof session.user.email === 'string'
	);
}

export function resolvePlaywrightSupabaseStorageKey(supabaseUrl: string): string {
	try {
		const hostname = new URL(supabaseUrl).hostname;
		const projectRef = hostname.split('.')[0] || '';
		return projectRef ? `sb-${projectRef}-auth-token` : '';
	} catch {
		return '';
	}
}

export function createPlaywrightE2EAccessToken(params: {
	secret: string;
	fixture?: PlaywrightE2EFixture;
	issuer?: string;
	nowMs?: number;
	lifetimeSeconds?: number;
}): string {
	const secret = String(params.secret || '').trim();
	if (!secret) {
		throw new Error('SUPABASE_JWT_SECRET is required for Playwright E2E access tokens.');
	}

	const fixture = params.fixture ?? resolvePlaywrightE2EFixture();
	const issuer = resolveValue(params.issuer, 'supabase');
	const issuedAt = Math.floor((params.nowMs ?? Date.now()) / 1000);
	const lifetimeSeconds = Math.max(60, Math.floor(params.lifetimeSeconds ?? 3600));
	const header = { alg: 'HS256', typ: 'JWT' };
	const payload = {
		aud: 'authenticated',
		iss: issuer,
		sub: fixture.userId,
		email: fixture.email,
		role: 'authenticated',
		iat: issuedAt,
		exp: issuedAt + lifetimeSeconds
	};

	const encodedHeader = encodeSegment(header);
	const encodedPayload = encodeSegment(payload);
	const signingInput = `${encodedHeader}.${encodedPayload}`;
	const signature = createHmac('sha256', secret).update(signingInput).digest('base64url');

	return `${signingInput}.${signature}`;
}

export function verifyPlaywrightE2EAccessToken(params: {
	token: string;
	secret: string;
	fixture?: PlaywrightE2EFixture;
	issuer?: string;
	nowMs?: number;
}): boolean {
	const token = String(params.token || '').trim();
	const secret = String(params.secret || '').trim();
	if (!token || !secret) {
		return false;
	}

	const fixture = params.fixture ?? resolvePlaywrightE2EFixture();
	const issuer = resolveValue(params.issuer, 'supabase');
	const [header, payload, signature] = token.split('.');
	if (!header || !payload || !signature) {
		return false;
	}

	const expectedSignature = createHmac('sha256', secret)
		.update(`${header}.${payload}`)
		.digest('base64url');
	if (!isTimingSafeEqual(signature, expectedSignature)) {
		return false;
	}

	try {
		const decodedHeader = decodeSegment(header);
		const decodedPayload = decodeSegment(payload);
		const now = Math.floor((params.nowMs ?? Date.now()) / 1000);

		return (
			decodedHeader.alg === 'HS256' &&
			decodedHeader.typ === 'JWT' &&
			decodedPayload.aud === 'authenticated' &&
			decodedPayload.iss === issuer &&
			decodedPayload.sub === fixture.userId &&
			decodedPayload.email === fixture.email &&
			decodedPayload.role === 'authenticated' &&
			typeof decodedPayload.exp === 'number' &&
			decodedPayload.exp >= now &&
			(typeof decodedPayload.iat !== 'number' || decodedPayload.iat <= now + 60)
		);
	} catch {
		return false;
	}
}

export function createPlaywrightE2EBrowserSession(params: {
	secret: string;
	fixture?: PlaywrightE2EFixture;
	issuer?: string;
	nowMs?: number;
	lifetimeSeconds?: number;
}): PlaywrightE2EBrowserSession {
	const fixture = params.fixture ?? resolvePlaywrightE2EFixture();
	const now = Math.floor((params.nowMs ?? Date.now()) / 1000);
	const expiresIn = Math.max(60, Math.floor(params.lifetimeSeconds ?? 12 * 60 * 60));
	const accessToken = createPlaywrightE2EAccessToken({
		secret: params.secret,
		issuer: params.issuer,
		fixture,
		nowMs: params.nowMs,
		lifetimeSeconds: expiresIn
	});

	return {
		access_token: accessToken,
		refresh_token: 'playwright-refresh-token',
		expires_in: expiresIn,
		expires_at: now + expiresIn,
		token_type: 'bearer',
		user: {
			id: fixture.userId,
			aud: 'authenticated',
			role: 'authenticated',
			email: fixture.email,
			email_confirmed_at: new Date(0).toISOString(),
			phone: '',
			app_metadata: { provider: 'email', providers: ['email'] },
			user_metadata: { name: fixture.userName, source: 'playwright' },
			identities: [],
			created_at: new Date(0).toISOString(),
			updated_at: new Date(params.nowMs ?? Date.now()).toISOString(),
			is_anonymous: false
		}
	};
}

export function encodePlaywrightE2EBrowserSessionCookie(params: {
	secret: string;
	fixture?: PlaywrightE2EFixture;
	issuer?: string;
	nowMs?: number;
	lifetimeSeconds?: number;
}): string {
	return `base64-${Buffer.from(JSON.stringify(createPlaywrightE2EBrowserSession(params))).toString(
		'base64url'
	)}`;
}

export function decodePlaywrightE2EBrowserSessionCookie(
	value: string | undefined | null
): PlaywrightE2EBrowserSession | null {
	const normalized = String(value || '').trim();
	if (!normalized) {
		return null;
	}

	const encoded = normalized.startsWith('base64-')
		? normalized.slice('base64-'.length)
		: normalized;
	try {
		const parsed = JSON.parse(Buffer.from(encoded, 'base64url').toString('utf8')) as unknown;
		return isPlaywrightBrowserSession(parsed) ? parsed : null;
	} catch {
		return null;
	}
}
