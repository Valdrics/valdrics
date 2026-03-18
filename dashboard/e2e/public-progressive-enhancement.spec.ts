import { expect, test } from '@playwright/test';

const BASE_URL = process.env.DASHBOARD_URL || 'http://localhost:4173';

test.describe('Public progressive enhancement', () => {
	test.use({ javaScriptEnabled: false });

	test('landing page exposes no-JS fallback links and readable SSR content', async ({ page }) => {
		await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });

		const banner = page.locator('[data-noscript-banner]');
		await expect(banner).toContainText(/javascript is disabled/i);
		await expect(page.locator('main')).toHaveCount(1);
		await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible();
		await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', `${BASE_URL}/`);

		await banner.getByRole('link', { name: /^resources$/i }).click();
		await expect(page).toHaveURL(/\/resources$/);
		await expect(page.getByRole('heading', { level: 1, name: /resources/i })).toBeVisible();

		await banner.getByRole('link', { name: /^status$/i }).click();
		await expect(page).toHaveURL(/\/status$/);
		await expect(page.getByRole('heading', { level: 1, name: /system status/i })).toBeVisible();
	});

	test('status and legal pages retain metadata and structured data without JavaScript', async ({
		page
	}) => {
		for (const routeCase of [
			{
				path: '/status',
				heading: /system status/i,
				title: /System Status \| Valdrics/i
			},
			{
				path: '/privacy',
				heading: /privacy policy/i,
				title: /Privacy Policy \| Valdrics/i
			},
			{
				path: '/terms',
				heading: /terms of service/i,
				title: /Terms of Service \| Valdrics/i
			}
		]) {
			await page.goto(`${BASE_URL}${routeCase.path}`, { waitUntil: 'domcontentloaded' });
			await expect(page).toHaveTitle(routeCase.title);
			await expect(page.getByRole('heading', { level: 1, name: routeCase.heading })).toBeVisible();
			await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', 'index,follow');
			await expect(page.locator('script[type="application/ld+json"]').first()).toBeAttached();
		}
	});
});
