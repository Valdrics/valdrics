import { expect, test } from '@playwright/test';

const runExpandedPublicVisuals = process.env.PLAYWRIGHT_PUBLIC_VISUAL_EXPANDED === '1';

async function prepareStablePublicPage(
	page: Parameters<typeof test>[0]['page'],
	path: string = '/'
) {
	await page.addInitScript(() => {
		const originalSetInterval = window.setInterval.bind(window);
		window.setInterval = ((handler: TimerHandler, timeout?: number, ...args: unknown[]) => {
			if (typeof timeout === 'number' && timeout >= 1000) {
				return 0 as unknown as number;
			}
			return originalSetInterval(handler, timeout, ...args);
		}) as typeof window.setInterval;
	});

	await page.emulateMedia({ reducedMotion: 'reduce' });
	await page.goto(path);
	await page.waitForLoadState('networkidle');
	await page.waitForTimeout(300);
}

test.describe('Landing visual snapshots', () => {
	test.describe('Desktop', () => {
		test.use({ viewport: { width: 1440, height: 900 } });

		test('hero and core sections stay visually stable', async ({ page }) => {
			await prepareStablePublicPage(page);
			await expect(page.locator('.landing-hero')).toHaveScreenshot('landing-hero-desktop.png', {
				animations: 'disabled',
				caret: 'hide'
			});
			await expect(page.locator('#capabilities')).toHaveScreenshot('landing-hook-desktop.png', {
				animations: 'disabled',
				caret: 'hide'
			});
			await expect(page.locator('#trust')).toHaveScreenshot('landing-trust-desktop.png', {
				animations: 'disabled',
				caret: 'hide'
			});
		});
	});

	test.describe('Mobile', () => {
		test.use({ viewport: { width: 390, height: 844 } });

		test('hero and core sections stay visually stable', async ({ page }) => {
			await prepareStablePublicPage(page);
			await expect(page.locator('.landing-hero')).toHaveScreenshot('landing-hero-mobile.png', {
				animations: 'disabled',
				caret: 'hide'
			});
			await expect(page.locator('#capabilities')).toHaveScreenshot('landing-hook-mobile.png', {
				animations: 'disabled',
				caret: 'hide'
			});
			await expect(page.locator('#trust')).toHaveScreenshot('landing-trust-mobile.png', {
				animations: 'disabled',
				caret: 'hide'
			});
		});
	});
});

if (runExpandedPublicVisuals) {
	test.describe('Public route visual snapshots', () => {
		test.describe('Desktop', () => {
			test.use({ viewport: { width: 1440, height: 900 } });

			test('core public routes stay visually stable', async ({ page }) => {
				await prepareStablePublicPage(page, '/docs');
				await expect(page.locator('.public-page')).toHaveScreenshot('public-docs-desktop.png', {
					animations: 'disabled',
					caret: 'hide'
				});

				await prepareStablePublicPage(page, '/docs/quick-start-workspace');
				await expect(page.locator('.public-article-page')).toHaveScreenshot(
					'public-doc-article-desktop.png',
					{
						animations: 'disabled',
						caret: 'hide'
					}
				);

				await prepareStablePublicPage(page, '/resources');
				await expect(page.locator('.public-page')).toHaveScreenshot(
					'public-resources-desktop.png',
					{
						animations: 'disabled',
						caret: 'hide'
					}
				);

				await prepareStablePublicPage(page, '/proof');
				await expect(page.locator('.public-page')).toHaveScreenshot('public-proof-desktop.png', {
					animations: 'disabled',
					caret: 'hide'
				});

				await prepareStablePublicPage(page, '/enterprise');
				await expect(page.locator('.enterprise-shell')).toHaveScreenshot(
					'public-enterprise-desktop.png',
					{
						animations: 'disabled',
						caret: 'hide'
					}
				);

				await prepareStablePublicPage(page, '/talk-to-sales');
				await expect(page.locator('.public-page')).toHaveScreenshot(
					'public-talk-to-sales-desktop.png',
					{
						animations: 'disabled',
						caret: 'hide'
					}
				);
			});
		});

		test.describe('Mobile', () => {
			test.use({ viewport: { width: 390, height: 844 } });

			test('core public routes stay visually stable', async ({ page }) => {
				await prepareStablePublicPage(page, '/docs');
				await expect(page.locator('.public-page')).toHaveScreenshot('public-docs-mobile.png', {
					animations: 'disabled',
					caret: 'hide'
				});

				await prepareStablePublicPage(page, '/docs/quick-start-workspace');
				await expect(page.locator('.public-article-page')).toHaveScreenshot(
					'public-doc-article-mobile.png',
					{
						animations: 'disabled',
						caret: 'hide'
					}
				);

				await prepareStablePublicPage(page, '/proof');
				await expect(page.locator('.public-page')).toHaveScreenshot('public-proof-mobile.png', {
					animations: 'disabled',
					caret: 'hide'
				});

				await prepareStablePublicPage(page, '/talk-to-sales');
				await expect(page.locator('.public-page')).toHaveScreenshot(
					'public-talk-to-sales-mobile.png',
					{
						animations: 'disabled',
						caret: 'hide'
					}
				);
			});
		});
	});
}
