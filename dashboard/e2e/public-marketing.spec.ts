import { expect, test } from '@playwright/test';

const BASE_URL = process.env.DASHBOARD_URL || 'http://localhost:4173';

async function assertPublicRoute(
	page: Parameters<typeof test>[0]['page'],
	path: string,
	heading: RegExp
) {
	await page.goto(`${BASE_URL}${path}`);
	await expect(page).toHaveURL(new RegExp(`${path.replace('/', '\\/')}(\\?.*)?$`));
	await expect(page.getByRole('heading', { level: 1, name: heading })).toBeVisible();
}

async function assertHashDestination(
	page: Parameters<typeof test>[0]['page'],
	hash: string,
	selector: string
) {
	await expect
		.poll(() => new URL(page.url()).hash, { message: `expected URL hash ${hash}` })
		.toBe(hash);
	await expect(page.locator(selector)).toBeVisible();
}

async function assertDownloadEndpoint(
	page: Parameters<typeof test>[0]['page'],
	path: string,
	expectedContentType?: RegExp
) {
	const response = await page.request.get(new URL(path, BASE_URL).toString());
	expect(response.ok()).toBeTruthy();
	if (expectedContentType) {
		expect(response.headers()['content-type'] || '').toMatch(expectedContentType);
	}
}

async function goToLanding(page: Parameters<typeof test>[0]['page']) {
	await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
	await expect(page.locator('#hero')).toBeVisible();
}

async function openResourcesMenu(page: Parameters<typeof test>[0]['page']) {
	const button = page.locator('header').getByRole('button', { name: /^resources$/i });
	await expect(button).toBeVisible();
	for (let attempt = 0; attempt < 2; attempt += 1) {
		const menu = page.locator('#public-resources-menu');
		if (await menu.isVisible().catch(() => false)) {
			return menu;
		}
		await button.click();
		if (await menu.isVisible().catch(() => false)) {
			return menu;
		}
		await page.waitForTimeout(150);
	}
	const menu = page.locator('#public-resources-menu');
	await expect(menu).toBeVisible();
	return menu;
}

async function openMobileMenu(page: Parameters<typeof test>[0]['page']) {
	const toggle = page.getByRole('button', { name: /toggle menu/i });
	await expect(toggle).toBeVisible();
	for (let attempt = 0; attempt < 2; attempt += 1) {
		const menu = page.locator('#public-mobile-menu');
		if (await menu.isVisible().catch(() => false)) {
			return menu;
		}
		await toggle.click();
		if (await menu.isVisible().catch(() => false)) {
			return menu;
		}
		await page.waitForTimeout(150);
	}
	const menu = page.locator('#public-mobile-menu');
	await expect(menu).toBeVisible();
	return menu;
}

test.describe('Public marketing smoke (desktop)', () => {
	test('covers landing, pricing, docs, api docs, and status navigation', async ({
		page
	}, testInfo) => {
		await goToLanding(page);

		await expect(
			page.getByRole('heading', {
				level: 1,
				name: /stop cloud and software waste|control every dollar|control cloud margin risk/i
			})
		).toBeVisible();
		await expect(page.getByRole('contentinfo')).toBeVisible();

		const primaryCta = page
			.getByRole('link', { name: /start free|book executive briefing/i })
			.first();
		await expect(primaryCta).toHaveAttribute('href', '/auth/login');

		const footer = page.getByRole('contentinfo');
		await footer.getByRole('link', { name: /documentation/i }).click();
		await expect(page).toHaveURL(/\/docs$/);
		await expect(page.getByRole('heading', { level: 1, name: /documentation/i })).toBeVisible();

		await page.getByRole('link', { name: /open api docs/i }).click();
		await expect(page).toHaveURL(/\/docs\/api$/);
		await expect(page.getByRole('heading', { level: 1, name: /api reference/i })).toBeVisible();

		await page.getByRole('link', { name: /system status/i }).click();
		await expect(page).toHaveURL(/\/status$/);
		await expect(page.getByRole('heading', { level: 1, name: /system status/i })).toBeVisible();

		await page.goto(`${BASE_URL}/pricing`);
		await expect(
			page.getByRole('heading', { level: 1, name: /simple, transparent pricing/i })
		).toBeVisible();
		const switchButton = page.getByRole('switch', { name: /toggle billing cycle/i });
		await expect(switchButton).toHaveAttribute('aria-checked', 'false');
		await switchButton.click();
		await expect(switchButton).toHaveAttribute('aria-checked', 'true');
		await page.screenshot({
			path: testInfo.outputPath('desktop-public-smoke.png'),
			fullPage: true
		});
	});

	test('keeps public header, resources, and hero CTAs on working destinations', async ({
		page
	}) => {
		await goToLanding(page);
		const header = page.locator('header');

		await header.getByRole('link', { name: /^product$/i }).click();
		await assertHashDestination(page, '#product', '#product');

		await goToLanding(page);
		await header.getByRole('link', { name: /^pricing$/i }).click();
		await assertPublicRoute(page, '/pricing', /simple, transparent pricing/i);

		await goToLanding(page);
		await header.getByRole('link', { name: /^enterprise$/i }).click();
		await assertPublicRoute(
			page,
			'/enterprise',
			/control cloud and software economics with procurement-grade confidence/i
		);

		await goToLanding(page);
		await (await openResourcesMenu(page)).getByRole('menuitem', { name: /^resource hub$/i }).click();
		await assertPublicRoute(page, '/resources', /resources/i);

		await goToLanding(page);
		await (await openResourcesMenu(page)).getByRole('menuitem', { name: /^docs$/i }).click();
		await assertPublicRoute(page, '/docs', /documentation/i);

		await goToLanding(page);
		await (await openResourcesMenu(page)).getByRole('menuitem', { name: /^proof pack$/i }).click();
		await assertPublicRoute(page, '/proof', /executive and technical proof for buyer diligence/i);

		await goToLanding(page);
		await (await openResourcesMenu(page)).getByRole('menuitem', { name: /^insights$/i }).click();
		await assertPublicRoute(page, '/insights', /insights/i);

		await goToLanding(page);
		await header.getByRole('link', { name: /^talk to sales$/i }).click();
		await assertPublicRoute(page, '/talk-to-sales', /talk to sales/i);

		await goToLanding(page);
		await header.getByRole('link', { name: /^start free$/i }).click();
		await expect(page).toHaveURL(/\/auth\/login(\?.*)?$/);

		await goToLanding(page);
		const hero = page.locator('#hero');
		await hero.getByRole('link', { name: /see enterprise path/i }).click();
		await assertPublicRoute(
			page,
			'/enterprise',
			/control cloud and software economics with procurement-grade confidence/i
		);

		await goToLanding(page);
		await hero.getByRole('link', { name: /start free|book executive briefing/i }).click();
		await expect(page).toHaveURL(/\/auth\/login(\?.*)?$/);

		await goToLanding(page);
		await page.locator('#simulator').getByRole('link', { name: /open full roi planner/i }).click();
		await expect(page).toHaveURL(/\/auth\/login(\?.*intent=roi_assessment.*)?$/);
	});

	test('keeps proof, pricing, trust, and footer CTAs on working destinations', async ({ page }) => {
		await goToLanding(page);
		const simulator = page.locator('#simulator');
		await simulator.getByRole('link', { name: /review methodology/i }).click();
		await assertPublicRoute(page, '/docs/technical-validation', /public capability validation summary/i);

		await goToLanding(page);
		const assumptionsHref = await simulator
			.getByRole('link', { name: /open assumptions csv/i })
			.getAttribute('href');
		expect(assumptionsHref || '').toMatch(/resources\/valdrics-roi-assumptions\.csv$/);
		if (assumptionsHref) {
			await assertDownloadEndpoint(page, assumptionsHref, /text\/csv|text\/plain/i);
		}

		await goToLanding(page);
		const plans = page.locator('#plans');
		await plans.getByRole('link', { name: /start on free tier/i }).click();
		await expect(page).toHaveURL(/\/auth\/login(\?.*plan=free.*)?$/);

		for (const label of [/^start with starter$/i, /^start with growth$/i, /^start with pro$/i]) {
			await goToLanding(page);
			await page.locator('#plans').getByRole('link', { name: label }).click();
			await expect(page).toHaveURL(/\/auth\/login(\?.*plan=.*)?$/);
		}

		await goToLanding(page);
		await plans.getByRole('link', { name: /view full pricing/i }).click();
		await assertPublicRoute(page, '/pricing', /simple, transparent pricing/i);

		await goToLanding(page);
		await plans.getByRole('link', { name: /^talk to sales$/i }).click();
		await assertPublicRoute(page, '/talk-to-sales', /talk to sales/i);

		await goToLanding(page);
		const trust = page.locator('#trust');
		const accessChecklistHref = await trust
			.getByRole('link', { name: /access control & compliance checklist/i })
			.getAttribute('href');
		expect(accessChecklistHref || '').toMatch(/resources\/global-finops-compliance-workbook\.md$/);
		if (accessChecklistHref) {
			await assertDownloadEndpoint(page, accessChecklistHref, /text\/markdown|text\/plain/i);
		}

		await goToLanding(page);
		await trust.getByRole('link', { name: /^talk to sales$/i }).click();
		await assertPublicRoute(page, '/talk-to-sales', /talk to sales/i);

		await goToLanding(page);
		const onePagerHref = await trust
			.getByRole('link', { name: /download executive one-pager/i })
			.getAttribute('href');
		expect(onePagerHref || '').toMatch(/resources\/valdrics-enterprise-one-pager\.md$/);
		if (onePagerHref) {
			await assertDownloadEndpoint(page, onePagerHref, /text\/markdown|text\/plain/i);
		}

		await goToLanding(page);
		await trust.getByRole('link', { name: /enterprise governance overview/i }).click();
		await assertPublicRoute(
			page,
			'/enterprise',
			/control cloud and software economics with procurement-grade confidence/i
		);

		await goToLanding(page);
		const workbookHref = await trust
			.getByRole('link', { name: /access control & compliance checklist/i })
			.getAttribute('href');
		expect(workbookHref || '').toMatch(/resources\/global-finops-compliance-workbook\.md$/);
		if (workbookHref) {
			await assertDownloadEndpoint(page, workbookHref, /text\/markdown|text\/plain/i);
		}

		const footerCases = [
			{ label: /documentation/i, type: 'route', path: '/docs', heading: /documentation/i },
			{ label: /api reference/i, type: 'route', path: '/docs/api', heading: /api reference/i },
			{ label: /^resources$/i, type: 'route', path: '/resources', heading: /resources/i },
			{
				label: /^enterprise$/i,
				type: 'route',
				path: '/enterprise',
				heading: /control cloud and software economics with procurement-grade confidence/i
			},
			{
				label: /^proof pack$/i,
				type: 'route',
				path: '/proof',
				heading: /executive and technical proof for buyer diligence/i
			},
			{ label: /^insights$/i, type: 'route', path: '/insights', heading: /insights/i },
			{ label: /^talk to sales$/i, type: 'route', path: '/talk-to-sales', heading: /talk to sales/i },
			{ label: /^pricing$/i, type: 'route', path: '/pricing', heading: /simple, transparent pricing/i },
			{ label: /^privacy$/i, type: 'route', path: '/privacy', heading: /privacy policy/i },
			{ label: /^terms$/i, type: 'route', path: '/terms', heading: /terms of service/i },
			{ label: /^status$/i, type: 'route', path: '/status', heading: /system status/i }
		] as const;

		for (const footerCase of footerCases) {
			await goToLanding(page);
			const footer = page.getByRole('contentinfo');
			const link = footer.getByRole('link', { name: footerCase.label });
			const href = await link.getAttribute('href');
			expect(href || '').toBeTruthy();
			if (href) {
				await page.goto(new URL(href, BASE_URL).toString(), { waitUntil: 'domcontentloaded' });
			}
			await assertPublicRoute(page, footerCase.path, footerCase.heading);
		}

		await goToLanding(page);
		const footer = page.getByRole('contentinfo');
		await expect(
			footer.getByRole('link', { name: /sales contact sales@valdrics.com/i })
		).toHaveAttribute('href', /^mailto:sales@valdrics\.com$/i);
		await expect(
			footer.getByRole('link', { name: /support contact support@valdrics.com/i })
		).toHaveAttribute('href', /^mailto:support@valdrics\.com$/i);
		await expect(
			footer.getByRole('link', { name: /security contact security@valdrics.com/i })
		).toHaveAttribute('href', /^mailto:security@valdrics\.com$/i);
	});
});

test.describe('Public marketing smoke (mobile)', () => {
	test.use({ viewport: { width: 390, height: 844 } });

	test('key landing sections and docs pages remain usable', async ({ page }, testInfo) => {
		await goToLanding(page);
		await expect(
			page.getByRole('heading', {
				level: 1,
				name: /stop cloud and software waste|control every dollar|control cloud margin risk/i
			})
		).toBeVisible();
		await expect(page.locator('#capabilities')).toBeVisible();
		await expect(page.locator('#simulator')).toBeVisible();
		await expect(page.locator('#plans')).toBeVisible();
		await expect(page.locator('#trust')).toBeVisible();

		await assertPublicRoute(page, '/docs', /documentation/i);
		await assertPublicRoute(page, '/docs/api', /api reference/i);
		await assertPublicRoute(page, '/status', /system status/i);
		await page.screenshot({
			path: testInfo.outputPath('mobile-public-smoke.png'),
			fullPage: true
		});
	});

	test('mobile menu links resolve key landing and route destinations', async ({ page }) => {
		await goToLanding(page);
		await (await openMobileMenu(page)).getByRole('link', { name: /^talk to sales$/i }).click();
		await assertPublicRoute(page, '/talk-to-sales', /talk to sales/i);

		await goToLanding(page);
		await (await openMobileMenu(page)).getByRole('link', { name: /^start free$/i }).click();
		await expect(page).toHaveURL(/\/auth\/login(\?.*)?$/);

		await goToLanding(page);
		await (await openMobileMenu(page)).getByRole('link', { name: /^product$/i }).click();
		await assertHashDestination(page, '#product', '#product');

		await goToLanding(page);
		await (await openMobileMenu(page)).getByRole('link', { name: /^pricing$/i }).click();
		await assertPublicRoute(page, '/pricing', /simple, transparent pricing/i);

		await goToLanding(page);
		await (await openMobileMenu(page)).getByRole('link', { name: /^enterprise$/i }).click();
		await assertPublicRoute(
			page,
			'/enterprise',
			/control cloud and software economics with procurement-grade confidence/i
		);

		await goToLanding(page);
		await (await openMobileMenu(page)).getByRole('link', { name: /^resources$/i }).click();
		await assertPublicRoute(page, '/resources', /resources/i);
	});
});
