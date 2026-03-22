/**
 * End-to-End Tests for Critical Paths
 *
 * Tests:
 * 1. Onboarding flow
 * 2. Billing flow
 * 3. Remediation approval
 */

import { test, expect, type Page } from '@playwright/test';
import { BASE_URL, enableAuthenticatedSession } from './support/e2eAuth';

// Helper to wait for page load
async function waitForPageLoad(page: Page) {
	await page.waitForLoadState('networkidle');
}

// ==================== Onboarding Flow ====================

test.describe('Onboarding Flow', () => {
	test('landing page loads correctly', async ({ page }) => {
		await page.goto(BASE_URL);
		await waitForPageLoad(page);

		await expect(
			page.getByRole('heading', {
				level: 1,
				name: /govern spend without slowing delivery|turn cloud, saas, and software spend into governed action without slowing delivery|control cloud spend decisions|protect margin with governed spend decisions|one governed path from variance to board-ready proof/i
			})
		).toBeVisible();
		await expect(
			page.getByRole('link', { name: /Start Free Workspace|Book Executive Briefing/i }).first()
		).toBeVisible();
		await expect(
			page.getByRole('link', { name: /See Pricing|Start Free Workspace/i }).nth(1)
		).toBeVisible();
	});

	test('skip link is keyboard reachable', async ({ page }) => {
		await page.goto(BASE_URL);

		// First focus should land on the skip link for keyboard users.
		await page.keyboard.press('Tab');
		const skipLink = page.locator('a.skip-link');
		await expect(skipLink).toBeFocused();
		await expect(skipLink).toHaveAttribute('href', '#main');
	});

	test('pricing page displays all tiers', async ({ page }) => {
		await page.goto(`${BASE_URL}/pricing`);
		await waitForPageLoad(page);

		await expect(page.getByRole('link', { name: /Start on Free Tier/i })).toBeVisible();
		await expect(page.getByRole('heading', { name: 'Starter', exact: true })).toBeVisible();
		await expect(page.getByRole('heading', { name: 'Growth', exact: true })).toBeVisible();
		await expect(page.getByRole('heading', { name: 'Pro', exact: true })).toBeVisible();
		await expect(page.getByRole('link', { name: /Open Enterprise Path/i })).toBeVisible();
	});

	test('login page loads', async ({ page }) => {
		await page.goto(`${BASE_URL}/auth/login`);
		await waitForPageLoad(page);

		await expect(page.getByLabel(/email address/i)).toBeVisible();
		await expect(page.getByRole('button', { name: /^sign in$/i })).toBeVisible();
		await expect(page.getByRole('button', { name: /continue with sso/i })).toBeVisible();
	});

	test('signup page loads', async ({ page }) => {
		await page.goto(`${BASE_URL}/auth/login`);
		await waitForPageLoad(page);

		await page.getByRole('button', { name: /^sign up$/i }).click();
		await expect(
			page.getByRole('heading', { level: 1, name: /create your account/i })
		).toBeVisible();
		await expect(page.getByRole('button', { name: /^create account$/i })).toBeVisible();
	});
});

// ==================== SEO / Indexability ====================

test.describe('SEO and Indexability', () => {
	test('robots.txt references sitemap', async ({ request }) => {
		const res = await request.get(`${BASE_URL}/robots.txt`);
		expect(res.ok()).toBeTruthy();
		const body = await res.text();
		expect(body).toContain('Sitemap:');
		expect(body).toContain('/sitemap.xml');
	});

	test('sitemap.xml includes marketing routes', async ({ request }) => {
		const res = await request.get(`${BASE_URL}/sitemap.xml`);
		expect(res.ok()).toBeTruthy();
		const body = await res.text();
		expect(body).toContain('<urlset');
		expect(body).toContain('/pricing');
	});
});

// ==================== Dashboard Flow ====================

test.describe('Dashboard Flow (Authenticated)', () => {
	test.beforeEach(async ({ context }) => {
		await enableAuthenticatedSession(context);
	});

	test('dashboard loads with key metrics', async ({ page }) => {
		await page.goto(`${BASE_URL}/dashboard`);
		await waitForPageLoad(page);

		// Dashboard should have these sections
		await expect(page.locator('h1:has-text("Dashboard")')).toBeVisible();
	});

	test('settings page loads', async ({ page }) => {
		const llmModelStatuses: number[] = [];
		page.on('response', (response) => {
			if (response.url().includes('/settings/llm/models')) {
				llmModelStatuses.push(response.status());
			}
		});

		await page.goto(`${BASE_URL}/settings`);
		await waitForPageLoad(page);

		await expect(page.locator('h1:has-text("Preferences")')).toBeVisible();
		expect(llmModelStatuses).not.toEqual([]);
		expect(llmModelStatuses).toEqual(expect.arrayContaining([200]));
		expect(llmModelStatuses).not.toContain(401);
	});
});

// ==================== Billing Flow ====================

test.describe('Billing Flow', () => {
	test.beforeEach(async ({ context }) => {
		await enableAuthenticatedSession(context);
	});

	test('billing page loads', async ({ page }) => {
		await page.goto(`${BASE_URL}/billing`);
		await waitForPageLoad(page);

		await expect(page.locator('h1:has-text("Subscription and usage")')).toBeVisible();
	});

	test('pricing cards are interactive', async ({ page }) => {
		await page.goto(`${BASE_URL}/pricing`);
		await waitForPageLoad(page);

		const ctaButton = page
			.getByRole('link', { name: /Start Free Workspace|Open Enterprise Path/i })
			.first();
		await expect(ctaButton).toBeVisible();

		await expect(ctaButton).toBeEnabled();
	});
});

// ==================== Connections Flow ====================

test.describe('Connections Flow', () => {
	test.beforeEach(async ({ context }) => {
		await enableAuthenticatedSession(context);
	});

	test('connections page loads', async ({ page }) => {
		await page.goto(`${BASE_URL}/connections`);
		await waitForPageLoad(page);

		await expect(page.locator('h1:has-text("Cloud Accounts")')).toBeVisible();
	});
});

// ==================== GreenOps Flow ====================

test.describe('GreenOps Flow', () => {
	test.beforeEach(async ({ context }) => {
		await enableAuthenticatedSession(context);
	});

	test('greenops page loads', async ({ page }) => {
		const greenopsStatuses = {
			carbon: [] as number[],
			budget: [] as number[],
			graviton: [] as number[],
			intensity: [] as number[]
		};
		page.on('response', (response) => {
			const url = response.url();
			if (url.includes('/carbon?')) {
				greenopsStatuses.carbon.push(response.status());
				return;
			}
			if (url.includes('/carbon/budget?')) {
				greenopsStatuses.budget.push(response.status());
				return;
			}
			if (url.includes('/carbon/graviton?')) {
				greenopsStatuses.graviton.push(response.status());
				return;
			}
			if (url.includes('/carbon/intensity?')) {
				greenopsStatuses.intensity.push(response.status());
			}
		});

		await page.goto(`${BASE_URL}/greenops`);
		await waitForPageLoad(page);

		await expect(page.getByRole('heading', { name: /greenops dashboard/i })).toBeVisible();
		await expect(page.getByText(/carbon/i).first()).toBeVisible();
		expect(greenopsStatuses.carbon).toEqual(expect.arrayContaining([200]));
		expect(greenopsStatuses.budget).toEqual(expect.arrayContaining([200]));
		expect(greenopsStatuses.graviton).toEqual(expect.arrayContaining([200]));
		expect(greenopsStatuses.intensity).toEqual(expect.arrayContaining([200]));
	});
});

// ==================== API Health Check ====================

test.describe('API Health', () => {
	test('health endpoint returns ok', async ({ request }) => {
		const apiUrl = process.env.API_URL || 'http://127.0.0.1:8000';

		const response = await request.get(`${apiUrl}/health`);
		expect(response.ok()).toBeTruthy();

		const body = await response.json();
		expect(['healthy', 'degraded', 'unknown']).toContain(body.status);
	});
});
