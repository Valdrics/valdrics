import { expect, test, type Page } from '@playwright/test';

import {
	BACKEND_URL,
	BASE_URL,
	E2E_FIXTURE,
	enableAuthenticatedSession,
	createFixtureAccessToken
} from './support/e2eAuth';

async function waitForIdle(page: Page) {
	await page.waitForLoadState('domcontentloaded');
}

function fixtureTierPattern() {
	return new RegExp(`${E2E_FIXTURE.tier}\\s+plan`, 'i');
}

test.describe('Authenticated shell', () => {
	test.beforeEach(async ({ context }) => {
		await enableAuthenticatedSession(context);
	});

	test('serves real seeded profile and subscription data from the backend', async ({ request }) => {
		const accessToken = createFixtureAccessToken();
		const headers = { Authorization: `Bearer ${accessToken}` };

		const [profileResponse, subscriptionResponse] = await Promise.all([
			request.get(`${BACKEND_URL}/api/v1/settings/profile`, { headers }),
			request.get(`${BACKEND_URL}/api/v1/billing/subscription`, { headers })
		]);

		expect(profileResponse.status()).toBe(200);
		expect(await profileResponse.json()).toMatchObject({
			email: E2E_FIXTURE.email,
			role: E2E_FIXTURE.role,
			persona: E2E_FIXTURE.persona,
			tier: E2E_FIXTURE.tier
		});

		expect(subscriptionResponse.status()).toBe(200);
		expect(await subscriptionResponse.json()).toMatchObject({
			tier: E2E_FIXTURE.tier,
			status: 'active'
		});
	});

	test('redirects authenticated landing visits to /dashboard', async ({ page }) => {
		await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
		await expect(page).toHaveURL(/\/dashboard(?:\?.*)?$/);
		await expect(page.getByRole('heading', { level: 1, name: /dashboard/i })).toBeVisible();
	});

	test('marks the active dashboard nav item and keeps persona extras collapsed by default', async ({
		page
	}) => {
		await page.goto(`${BASE_URL}/dashboard`);
		await waitForIdle(page);

		const sidebar = page.locator('#sidebar');
		await expect(sidebar).toBeVisible();
		await expect(sidebar).toContainText(E2E_FIXTURE.email);
		await expect(sidebar).toContainText(fixtureTierPattern());
		await expect(sidebar.getByRole('link', { name: /dashboard/i })).toHaveAttribute(
			'aria-current',
			'page'
		);

		const showAllButton = sidebar.locator('button[aria-controls="sidebar-more-nav"]');
		await expect(showAllButton).toHaveAttribute('aria-expanded', 'false');
		await expect(sidebar.getByRole('link', { name: /leaderboards/i })).toHaveCount(0);

		await showAllButton.click();
		await expect(showAllButton).toHaveAttribute('aria-expanded', 'true');
		await expect(sidebar.getByRole('link', { name: /leaderboards/i })).toBeVisible();
		await expect(sidebar.getByRole('link', { name: /billing/i })).toBeVisible();
	});

	test('opens the command palette and routes to LLM usage', async ({ page }) => {
		await page.goto(`${BASE_URL}/dashboard`);
		await waitForIdle(page);

		await page.getByRole('button', { name: /open command palette/i }).click();
		const dialog = page.getByRole('dialog', { name: /command palette/i });
		await expect(dialog).toBeVisible();

		const input = dialog.getByPlaceholder(/search actions, routes, or documentation/i);
		await input.fill('llm');
		await dialog.getByRole('button', { name: /llm usage/i }).click();

		await expect(page).toHaveURL(/\/llm(?:\?.*)?$/);
		await expect(page.getByRole('heading', { level: 1, name: /^llm usage$/i })).toBeVisible();
		await expect(
			page.locator('#sidebar').getByRole('link', { name: /llm usage/i })
		).toHaveAttribute('aria-current', 'page');
	});

	test('sidebar toggle updates expanded state for keyboard-first navigation', async ({ page }) => {
		await page.goto(`${BASE_URL}/dashboard`);
		await waitForIdle(page);

		const toggle = page.getByRole('button', { name: /toggle sidebar/i });
		const sidebar = page.locator('#sidebar');
		await expect(toggle).toHaveAttribute('aria-controls', 'sidebar');
		await expect(toggle).toHaveAttribute('aria-expanded', 'true');
		await expect(sidebar).toBeVisible();

		await toggle.click();
		await expect(toggle).toHaveAttribute('aria-expanded', 'false');
		await expect(sidebar).toBeVisible();

		await toggle.click();
		await expect(toggle).toHaveAttribute('aria-expanded', 'true');
	});

	test('seeds a supabase session cookie that can authenticate protected routes without the bypass header', async ({
		context,
		page
	}) => {
		await enableAuthenticatedSession(context, { browserSession: true });
		await context.setExtraHTTPHeaders({});

		await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'domcontentloaded' });
		await expect(page).toHaveURL(/\/dashboard(?:\?.*)?$/);
		await expect(page.getByRole('heading', { level: 1, name: /dashboard/i })).toBeVisible();
	});
});
