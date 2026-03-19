import { test, expect } from '@playwright/test';
import { enableAuthenticatedSession } from '../../e2e/support/e2eAuth';

test.describe('Authentication Flow', () => {
	test('shows landing page when not authenticated', async ({ page }) => {
		await page.goto('/');
		await expect(page.locator('h1')).toContainText(
			/govern cloud, saas, and software spend without slowing delivery/i
		);
	});

	test('shows sign in button on login page', async ({ page }) => {
		await page.goto('/auth/login');
		await expect(page.getByRole('button', { name: /Sign in/i })).toBeVisible();
	});
});

test.describe('Route Guards', () => {
	test('redirects unauthenticated user from settings to login', async ({ page }) => {
		await page.goto('/settings');
		await expect(page).toHaveURL(/\/auth\/login/);
	});
});

test.describe('Authenticated Route Access (test-mode)', () => {
	test.beforeEach(async ({ context }) => {
		await enableAuthenticatedSession(context);
	});

	test('loads dashboard shell with authenticated heading', async ({ page }) => {
		await page.goto('/');
		await expect(page).toHaveURL(/\/dashboard(?:\?.*)?$/);
		await expect(page.locator('h1')).toContainText(/Dashboard/i);
	});

	test('loads settings page when test auth header is set', async ({ page }) => {
		await page.goto('/settings');
		await expect(page).toHaveURL(/\/settings$/);
		await expect(page.locator('h1')).toContainText('Preferences');
	});
});
