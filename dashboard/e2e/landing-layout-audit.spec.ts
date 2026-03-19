import { expect, test } from '@playwright/test';

test.describe('Landing layout audit regressions', () => {
	test.use({ reducedMotion: 'reduce' });

	test('keeps approval-chain nodes, rail stops, and stage cards synchronized', async ({ page }) => {
		await page.setViewportSize({ width: 1365, height: 820 });
		await page.goto('/');
		await page.waitForLoadState('networkidle');

		const signalSection = page.locator('section#signal-map');
		await signalSection.scrollIntoViewIfNeeded();
		await expect(page.locator('section#signal-map .signal-map')).toBeVisible();

		const initialState = await signalSection.evaluate((section) => {
			const orbitNodes = Array.from(
				section.querySelectorAll<HTMLElement>('.approval-chain-orbit-node')
			);
			const railStops = Array.from(
				section.querySelectorAll<HTMLElement>('.approval-chain-rail-stop')
			);
			const stages = Array.from(section.querySelectorAll<HTMLElement>('.approval-chain-stage'));
			const titles = stages.map(
				(stage) => stage.querySelector('.approval-chain-stage-title')?.textContent?.trim() ?? ''
			);
			const activeOrbitIndex = orbitNodes.findIndex((node) => node.classList.contains('is-active'));
			const activeRailIndex = railStops.findIndex((stop) => stop.classList.contains('is-active'));
			const activeStageIndex = stages.findIndex((stage) => stage.classList.contains('is-active'));
			return {
				orbitCount: orbitNodes.length,
				railCount: railStops.length,
				stageCount: stages.length,
				titles,
				activeOrbitIndex,
				activeRailIndex,
				activeStageIndex
			};
		});

		expect(initialState.orbitCount).toBe(4);
		expect(initialState.railCount).toBe(4);
		expect(initialState.stageCount).toBe(4);
		expect(initialState.titles).toEqual([
			'Signal Scoped',
			'Checks Applied',
			'Approval Routed',
			'Outcome Recorded'
		]);
		expect(initialState.activeOrbitIndex).toBeGreaterThanOrEqual(0);
		expect(initialState.activeOrbitIndex).toBe(initialState.activeRailIndex);
		expect(initialState.activeOrbitIndex).toBe(initialState.activeStageIndex);

		const thirdStage = signalSection.locator('.approval-chain-stage').nth(2);
		await thirdStage.evaluate((element) => {
			(element as HTMLButtonElement).click();
		});
		await expect(signalSection.locator('#signal-control-details')).toBeVisible();

		await expect
			.poll(async () => {
				return signalSection.evaluate((section) => {
					const orbitNodes = Array.from(
						section.querySelectorAll<HTMLElement>('.approval-chain-orbit-node')
					);
					const railStops = Array.from(
						section.querySelectorAll<HTMLElement>('.approval-chain-rail-stop')
					);
					const stages = Array.from(section.querySelectorAll<HTMLElement>('.approval-chain-stage'));
					return {
						activeOrbitIndex: orbitNodes.findIndex((node) => node.classList.contains('is-active')),
						activeRailIndex: railStops.findIndex((stop) => stop.classList.contains('is-active')),
						activeStageIndex: stages.findIndex((stage) => stage.classList.contains('is-active'))
					};
				});
			})
			.toEqual({
				activeOrbitIndex: 2,
				activeRailIndex: 2,
				activeStageIndex: 2
			});
		await expect(signalSection.getByRole('tabpanel')).toContainText(/approval routed/i);
	});

	test('does not trigger unresolved Supabase host errors on anonymous landing loads', async ({
		page
	}) => {
		const failedRequests: { url: string; reason: string }[] = [];
		const consoleErrors: string[] = [];

		page.on('requestfailed', (request) => {
			const failure = request.failure();
			failedRequests.push({
				url: request.url(),
				reason: failure?.errorText ?? 'unknown'
			});
		});

		page.on('console', (message) => {
			if (message.type() !== 'error') return;
			consoleErrors.push(message.text());
		});

		await page.goto('/');
		await page.waitForLoadState('networkidle');

		const supabaseDnsFailures = failedRequests.filter((entry) =>
			entry.url.includes('.supabase.co')
		);
		const unresolvedErrors = consoleErrors.filter((entry) =>
			/ERR_NAME_NOT_RESOLVED|dns/i.test(entry)
		);

		expect(supabaseDnsFailures).toEqual([]);
		expect(unresolvedErrors).toEqual([]);
	});

	test.describe('mobile viewport 390', () => {
		test.use({ viewport: { width: 390, height: 844 } });

		test('prevents horizontal overflow and keeps sr-only clipped', async ({ page }) => {
			await page.goto('/');
			await page.waitForLoadState('networkidle');

			const overflow = await page.evaluate(() => ({
				scrollWidth: document.documentElement.scrollWidth,
				viewportWidth: window.innerWidth
			}));
			expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.viewportWidth + 1);

			const srOnlyMetrics = await page.locator('#signal-map-summary').evaluate((element) => {
				const node = element as HTMLElement;
				const style = window.getComputedStyle(node);
				const rect = node.getBoundingClientRect();
				return {
					width: rect.width,
					height: rect.height,
					position: style.position,
					overflow: style.overflow,
					whiteSpace: style.whiteSpace
				};
			});

			expect(srOnlyMetrics.width).toBeLessThanOrEqual(2);
			expect(srOnlyMetrics.height).toBeLessThanOrEqual(2);
			expect(srOnlyMetrics.position).toBe('absolute');
			expect(srOnlyMetrics.overflow).toBe('hidden');
			expect(srOnlyMetrics.whiteSpace).toBe('nowrap');

			const switchOverflow = await page.locator('.landing-hook-switch').evaluate((element) => ({
				scrollWidth: element.scrollWidth,
				clientWidth: element.clientWidth
			}));
			expect(switchOverflow.scrollWidth).toBeLessThanOrEqual(switchOverflow.clientWidth + 1);

			const withValdricsToggle = page.getByRole('button', { name: /^With Valdrics$/i });
			await expect(withValdricsToggle).toBeVisible();
			const toggleBounds = await withValdricsToggle.boundingBox();
			expect(toggleBounds).not.toBeNull();
			if (toggleBounds) {
				expect(toggleBounds.x).toBeGreaterThanOrEqual(0);
				expect(toggleBounds.x + toggleBounds.width).toBeLessThanOrEqual(390);
			}

			await page.evaluate(() => {
				window.scrollTo({ top: Math.round(document.documentElement.scrollHeight * 0.35) });
			});
			await page.waitForTimeout(120);

			const backToTop = page.getByRole('link', { name: /back to top/i });
			await expect(backToTop).toBeVisible();

			const progressWidthPx = await page
				.locator('.landing-scroll-progress > span')
				.evaluate((element) => {
					const rect = (element as HTMLElement).getBoundingClientRect();
					return rect.width;
				});
			expect(progressWidthPx).toBeGreaterThan(0);
		});
	});

	test.describe('mobile viewport 500', () => {
		test.use({ viewport: { width: 500, height: 900 } });

		test('keeps header actions on-screen at mobile/tablet breakpoint', async ({ page }) => {
			await page.goto('/');
			await page.waitForLoadState('networkidle');

			const headerOverflow = await page.evaluate(() => ({
				scrollWidth: document.documentElement.scrollWidth,
				viewportWidth: window.innerWidth
			}));
			expect(headerOverflow.scrollWidth).toBeLessThanOrEqual(headerOverflow.viewportWidth + 1);

			const menuToggle = page.getByRole('button', { name: /toggle menu/i });
			await expect(menuToggle).toBeVisible();
			const toggleBounds = await menuToggle.boundingBox();
			expect(toggleBounds).not.toBeNull();
			if (toggleBounds) {
				expect(toggleBounds.x).toBeGreaterThanOrEqual(0);
				expect(toggleBounds.x + toggleBounds.width).toBeLessThanOrEqual(500);
			}

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
