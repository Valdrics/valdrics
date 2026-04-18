import { expect, test } from '@playwright/test';

async function attachSecurityGuards(page: Parameters<typeof test>[0]['page']) {
	await page.addInitScript(() => {
		(
			window as Window & {
				__valdricsSecurityPolicyViolations?: { directive: string; blockedURI: string }[];
			}
		).__valdricsSecurityPolicyViolations = [];
		window.addEventListener('securitypolicyviolation', (event) => {
			(
				window as Window & {
					__valdricsSecurityPolicyViolations?: { directive: string; blockedURI: string }[];
				}
			).__valdricsSecurityPolicyViolations?.push({
				directive: event.violatedDirective,
				blockedURI: event.blockedURI
			});
		});
	});

	const consoleErrors: string[] = [];
	page.on('console', (message) => {
		if (message.type() !== 'error') return;
		if (
			/content security policy|securitypolicyviolation|refused to apply inline/i.test(
				message.text()
			)
		) {
			consoleErrors.push(message.text());
		}
	});

	return {
		async assertClean() {
			const securityPolicyViolations = await page.evaluate(() => {
				return (
					(
						window as Window & {
							__valdricsSecurityPolicyViolations?: { directive: string; blockedURI: string }[];
						}
					).__valdricsSecurityPolicyViolations ?? []
				);
			});
			expect(securityPolicyViolations).toEqual([]);
			expect(consoleErrors).toEqual([]);
		}
	};
}

test.describe('Landing layout audit regressions', () => {
	test.use({ reducedMotion: 'reduce' });

	test('keeps the public landing concise, structured, and CSP-clean', async ({ page }) => {
		const security = await attachSecurityGuards(page);
		await page.setViewportSize({ width: 1365, height: 820 });
		await page.goto('/');
		await page.waitForLoadState('networkidle');

		for (const sectionId of ['#hero', '#product', '#simulator', '#plans', '#trust']) {
			await expect(page.locator(sectionId)).toBeVisible();
		}

		await expect(page.locator('#hero')).toContainText(
			/control cloud spend without slowing delivery/i
		);
		await expect(page.locator('#hero .landing-public-proof-item')).toHaveCount(3);
		await expect(page.locator('#product .landing-public-pillar-card')).toHaveCount(3);
		await expect(page.locator('#plans .landing-public-plan-card')).toHaveCount(3);
		await expect(page.locator('#trust .landing-public-trust-card')).toHaveCount(3);

		const overflow = await page.evaluate(() => ({
			scrollWidth: document.documentElement.scrollWidth,
			viewportWidth: window.innerWidth
		}));
		expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.viewportWidth + 1);

		await security.assertClean();
	});

	test.describe('mobile viewport 390', () => {
		test.use({ viewport: { width: 390, height: 844 } });

		test('keeps mobile landing and footer chips inside the viewport', async ({ page }) => {
			const security = await attachSecurityGuards(page);
			await page.goto('/');
			await page.waitForLoadState('networkidle');

			const overflow = await page.evaluate(() => ({
				scrollWidth: document.documentElement.scrollWidth,
				viewportWidth: window.innerWidth
			}));
			expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.viewportWidth + 1);

			await page.evaluate(() => {
				window.scrollTo({ top: Math.round(document.documentElement.scrollHeight * 0.38) });
			});
			await page.waitForTimeout(120);

			await expect(page.getByRole('link', { name: /back to top/i })).toBeVisible();

			const lastBadge = page.getByRole('contentinfo').locator('.public-footer-contact').last();
			await lastBadge.scrollIntoViewIfNeeded();
			const badgeBounds = await lastBadge.boundingBox();
			expect(badgeBounds).not.toBeNull();
			if (badgeBounds) {
				expect(badgeBounds.x).toBeGreaterThanOrEqual(0);
				expect(badgeBounds.x + badgeBounds.width).toBeLessThanOrEqual(390);
			}

			await security.assertClean();
		});
	});

	test.describe('mobile viewport 500', () => {
		test.use({ viewport: { width: 500, height: 900 } });

		test('keeps header actions on-screen at mobile breakpoint', async ({ page }) => {
			await page.goto('/');
			await page.waitForLoadState('networkidle');

			const headerOverflow = await page.evaluate(() => ({
				scrollWidth: document.documentElement.scrollWidth,
				viewportWidth: window.innerWidth
			}));
			expect(headerOverflow.scrollWidth).toBeLessThanOrEqual(headerOverflow.viewportWidth + 1);

			const menuToggle = page.getByRole('button', { name: /toggle menu/i });
			await expect(menuToggle).toBeVisible();
			await menuToggle.click();

			const mobileStartFree = page.locator('#public-mobile-menu a', { hasText: 'Start Free' });
			await expect(mobileStartFree).toBeVisible();
			const ctaBounds = await mobileStartFree.boundingBox();
			expect(ctaBounds).not.toBeNull();
			if (ctaBounds) {
				expect(ctaBounds.x).toBeGreaterThanOrEqual(0);
				expect(ctaBounds.x + ctaBounds.width).toBeLessThanOrEqual(500);
			}
		});
	});
});
