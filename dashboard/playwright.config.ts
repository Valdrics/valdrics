import { defineConfig } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

delete process.env.NO_COLOR;

const isPublicOnly = process.env.PLAYWRIGHT_PUBLIC_ONLY === '1';
const skipManagedWebServer = process.env.PLAYWRIGHT_SKIP_WEBSERVER === '1';
const usePrebuiltPreview = process.env.PLAYWRIGHT_USE_PREBUILT_PREVIEW === '1';

function readDashboardEnvValue(name: string): string {
	try {
		const envText = readFileSync(resolve(process.cwd(), '.env'), 'utf8');
		for (const line of envText.split(/\r?\n/)) {
			if (!line.startsWith(`${name}=`)) {
				continue;
			}
			return line.slice(name.length + 1).trim();
		}
	} catch {
		return '';
	}

	return '';
}

function resolveSupabaseStorageKey(supabaseUrl: string): string {
	try {
		const hostname = new URL(supabaseUrl).hostname;
		const projectRef = hostname.split('.')[0] || '';
		return projectRef ? `sb-${projectRef}-auth-token` : '';
	} catch {
		return '';
	}
}

const defaultE2EEnv = {
	E2E_AUTH_SECRET: 'playwright',
	SUPABASE_JWT_SECRET: 'test-jwt-secret-at-least-32-bytes-long',
	SUPABASE_JWT_ISSUER: 'supabase',
	PLAYWRIGHT_E2E_DATABASE_URL: 'sqlite+aiosqlite:////tmp/valdrics-dashboard-playwright.sqlite3',
	PLAYWRIGHT_BACKEND_URL: 'http://127.0.0.1:8000',
	PLAYWRIGHT_E2E_TENANT_ID: '11111111-1111-4111-8111-111111111111',
	PLAYWRIGHT_E2E_TENANT_NAME: 'Playwright Test Tenant',
	PLAYWRIGHT_E2E_USER_ID: '22222222-2222-4222-8222-222222222222',
	PLAYWRIGHT_E2E_USER_NAME: 'E2E Test User',
	PLAYWRIGHT_E2E_USER_EMAIL: 'e2e@valdrics.test',
	PLAYWRIGHT_E2E_USER_ROLE: 'admin',
	PLAYWRIGHT_E2E_USER_PERSONA: 'engineering',
	PLAYWRIGHT_E2E_TIER: 'growth'
} as const;

const publicSupabaseUrl =
	process.env.PUBLIC_SUPABASE_URL || readDashboardEnvValue('PUBLIC_SUPABASE_URL');
const supabaseStorageKey =
	process.env.PLAYWRIGHT_SUPABASE_STORAGE_KEY || resolveSupabaseStorageKey(publicSupabaseUrl);

for (const [key, value] of Object.entries(defaultE2EEnv)) {
	process.env[key] ||= value;
}
if (publicSupabaseUrl) {
	process.env.PUBLIC_SUPABASE_URL ||= publicSupabaseUrl;
}
if (supabaseStorageKey) {
	process.env.PLAYWRIGHT_SUPABASE_STORAGE_KEY ||= supabaseStorageKey;
}

function shellEscape(value: string): string {
	return `'${value.replaceAll("'", "'\\''")}'`;
}

function buildShellEnv(envEntries: Record<string, string>): string {
	return Object.entries(envEntries)
		.map(([key, value]) => `${key}=${shellEscape(value)}`)
		.join(' ');
}

const sharedE2EEnv = {
	TESTING: 'true',
	E2E_AUTH_SECRET: process.env.E2E_AUTH_SECRET || defaultE2EEnv.E2E_AUTH_SECRET,
	E2E_ALLOW_PROD_PREVIEW: 'true',
	SUPABASE_JWT_SECRET: process.env.SUPABASE_JWT_SECRET || defaultE2EEnv.SUPABASE_JWT_SECRET,
	SUPABASE_JWT_ISSUER: process.env.SUPABASE_JWT_ISSUER || defaultE2EEnv.SUPABASE_JWT_ISSUER,
	PLAYWRIGHT_E2E_TENANT_ID:
		process.env.PLAYWRIGHT_E2E_TENANT_ID || defaultE2EEnv.PLAYWRIGHT_E2E_TENANT_ID,
	PLAYWRIGHT_E2E_TENANT_NAME:
		process.env.PLAYWRIGHT_E2E_TENANT_NAME || defaultE2EEnv.PLAYWRIGHT_E2E_TENANT_NAME,
	PLAYWRIGHT_E2E_USER_ID:
		process.env.PLAYWRIGHT_E2E_USER_ID || defaultE2EEnv.PLAYWRIGHT_E2E_USER_ID,
	PLAYWRIGHT_E2E_USER_NAME:
		process.env.PLAYWRIGHT_E2E_USER_NAME || defaultE2EEnv.PLAYWRIGHT_E2E_USER_NAME,
	PLAYWRIGHT_E2E_USER_EMAIL:
		process.env.PLAYWRIGHT_E2E_USER_EMAIL || defaultE2EEnv.PLAYWRIGHT_E2E_USER_EMAIL,
	PLAYWRIGHT_E2E_USER_ROLE:
		process.env.PLAYWRIGHT_E2E_USER_ROLE || defaultE2EEnv.PLAYWRIGHT_E2E_USER_ROLE,
	PLAYWRIGHT_E2E_USER_PERSONA:
		process.env.PLAYWRIGHT_E2E_USER_PERSONA || defaultE2EEnv.PLAYWRIGHT_E2E_USER_PERSONA,
	PLAYWRIGHT_E2E_TIER: process.env.PLAYWRIGHT_E2E_TIER || defaultE2EEnv.PLAYWRIGHT_E2E_TIER
};

const frontendEnv = buildShellEnv(sharedE2EEnv);
const backendEnv = buildShellEnv({
	...sharedE2EEnv,
	DATABASE_URL:
		process.env.PLAYWRIGHT_E2E_DATABASE_URL || defaultE2EEnv.PLAYWRIGHT_E2E_DATABASE_URL,
	DEBUG: 'false',
	ENCRYPTION_KEY: '32-byte-long-test-encryption-key',
	CSRF_SECRET_KEY: '32-byte-long-test-csrf-secret-key',
	KDF_SALT: 'S0RGX1NBTFRfRk9SX1RFU1RJTkdfMzJfQllURVNfT0s='
});

const webServer = [
	{
		command: usePrebuiltPreview
			? `${frontendEnv} pnpm run preview`
			: `${frontendEnv} pnpm run build && ${frontendEnv} pnpm run preview`,
		port: 4173,
		reuseExistingServer: false
	}
];

if (!isPublicOnly) {
	webServer.push({
		command: `cd .. && ${backendEnv} uv run python3 scripts/run_dashboard_playwright_backend.py --host 127.0.0.1 --port 8000`,
		port: 8000,
		reuseExistingServer: false
	});
}

export default defineConfig({
	use: {
		baseURL: process.env.DASHBOARD_URL || 'http://localhost:4173'
	},
	webServer: skipManagedWebServer ? undefined : webServer,
	testDir: '.',
	testMatch: ['tests/e2e/**/*.{test,spec}.ts', 'e2e/**/*.{test,spec}.ts']
});
