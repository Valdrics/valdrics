import { expect, test } from '@playwright/test';

const BASE_URL = process.env.DASHBOARD_URL || 'http://localhost:4173';
const LOCAL_DASHBOARD_HOSTS = new Set(['localhost', '127.0.0.1', '::1']);
const isLocalDashboardUrl = LOCAL_DASHBOARD_HOSTS.has(new URL(BASE_URL).hostname);

test.setTimeout(120_000);

async function attachSecurityGuards(page: Parameters<typeof test>[0]['page']) {
	await page.addInitScript(() => {
		const isKnownPassiveCspReport = (event: SecurityPolicyViolationEvent) => {
			const directive = event.effectiveDirective || event.violatedDirective;
			const blockedURI = event.blockedURI || '';
			let blockedUrl: URL;
			try {
				blockedUrl = new URL(blockedURI, window.location.href);
			} catch {
				return false;
			}

			// Chromium can report SvelteKit modulepreload headers and Cloudflare edge
			// injections as CSP violations even when the app scripts hydrate correctly.
			if (
				directive === 'script-src-elem' &&
				blockedUrl.origin === window.location.origin &&
				blockedUrl.pathname.startsWith('/_app/immutable/')
			) {
				return true;
			}

			if (
				directive === 'script-src-elem' &&
				blockedUrl.origin === window.location.origin &&
				blockedUrl.pathname.startsWith('/cdn-cgi/scripts/')
			) {
				return true;
			}

			if (
				directive === 'connect-src' &&
				blockedUrl.origin === window.location.origin &&
				blockedUrl.pathname === '/cdn-cgi/rum'
			) {
				return true;
			}

			return (
				directive === 'script-src-elem' &&
				blockedUrl.origin === 'https://static.cloudflareinsights.com' &&
				blockedUrl.pathname.startsWith('/beacon.min.js')
			);
		};

		(
			window as Window & {
				__valdricsSecurityPolicyViolations?: { directive: string; blockedURI: string }[];
			}
		).__valdricsSecurityPolicyViolations = [];
		window.addEventListener('securitypolicyviolation', (event) => {
			if (isKnownPassiveCspReport(event)) return;
			(
				window as Window & {
					__valdricsSecurityPolicyViolations?: { directive: string; blockedURI: string }[];
				}
			).__valdricsSecurityPolicyViolations?.push({
				directive: event.effectiveDirective || event.violatedDirective,
				blockedURI: event.blockedURI
			});
		});
	});

	const consoleErrors: string[] = [];
	const knownPassiveCspConsolePattern =
		/(_app\/immutable\/|\/cdn-cgi\/scripts\/|\/cdn-cgi\/rum\?|static\.cloudflareinsights\.com\/beacon\.min\.js)/i;
	page.on('console', (message) => {
		if (message.type() !== 'error') return;
		if (knownPassiveCspConsolePattern.test(message.text())) return;
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
	await expect(page.locator('.public-site-shell[data-public-hydrated="true"]')).toBeVisible();
}

async function ensureInteractiveSimulator(page: Parameters<typeof test>[0]['page']) {
	for (let attempt = 0; attempt < 3; attempt += 1) {
		const simulator = page.locator('#simulator');
		await expect(simulator).toBeVisible();
		try {
			await simulator.evaluate((element) => {
				element.scrollIntoView({ block: 'center', behavior: 'instant' });
			});
			break;
		} catch (error) {
			if (!/not attached to the DOM/i.test(String(error)) || attempt === 2) {
				throw error;
			}
			await page.waitForTimeout(150);
		}
	}
	const simulator = page.locator('#simulator');
	await expect(
		simulator.getByRole('heading', { name: /model the savings case in minutes/i })
	).toBeVisible();
	await expect(simulator.getByRole('group', { name: /display currency/i })).toBeVisible();
	return simulator;
}

async function ensureInteractivePlans(page: Parameters<typeof test>[0]['page']) {
	await ensureInteractiveSimulator(page);
	await page.evaluate(() => {
		window.scrollTo({ top: document.body.scrollHeight, behavior: 'instant' });
	});
	const plans = page.locator('#plans');
	await expect(plans.getByRole('link', { name: /start free workspace/i })).toBeVisible();
	return plans;
}

async function ensureInteractiveTrust(page: Parameters<typeof test>[0]['page']) {
	await ensureInteractivePlans(page);
	const trust = page.locator('#trust');
	await expect(trust.getByRole('link', { name: /open proof pack/i })).toBeVisible();
	return trust;
}

async function openResourcesMenu(page: Parameters<typeof test>[0]['page']) {
	await expect(page.locator('.public-site-shell[data-public-hydrated="true"]')).toBeVisible();
	const button = page.locator('header').getByRole('button', { name: /^resources$/i });
	await expect(button).toBeVisible();
	for (let attempt = 0; attempt < 4; attempt += 1) {
		const menu = page.locator('#public-resources-menu');
		if (await menu.isVisible().catch(() => false)) {
			return menu;
		}
		await button.click();
		await expect(button)
			.toHaveAttribute('aria-expanded', 'true', { timeout: 2_000 })
			.catch(async () => {
				await page.waitForTimeout(250);
			});
		if (await menu.isVisible({ timeout: 1_000 }).catch(() => false)) {
			return menu;
		}
		await page.keyboard.press('Escape').catch(() => undefined);
	}
	const menu = page.locator('#public-resources-menu');
	await expect(menu).toBeVisible();
	return menu;
}

async function openMobileMenu(page: Parameters<typeof test>[0]['page']) {
	const menu = page.locator('#public-mobile-menu');
	const toggle = page.getByRole('button', { name: /toggle menu/i });
	await expect(toggle).toBeVisible();

	if (await menu.isVisible().catch(() => false)) {
		return menu;
	}

	if ((await toggle.getAttribute('aria-expanded')) === 'true') {
		await menu.waitFor({ state: 'visible', timeout: 1_500 }).catch(async () => {
			await page.keyboard.press('Escape');
			await expect(toggle).toHaveAttribute('aria-expanded', 'false');
		});
		if (await menu.isVisible().catch(() => false)) {
			return menu;
		}
	}

	const backdrop = page.getByRole('button', { name: /close navigation menu/i });
	if (await backdrop.isVisible().catch(() => false)) {
		await page.keyboard.press('Escape');
		await expect(backdrop).toBeHidden();
	}

	for (let attempt = 0; attempt < 2; attempt += 1) {
		if (await menu.isVisible().catch(() => false)) {
			return menu;
		}
		await toggle.click();
		await menu.waitFor({ state: 'visible', timeout: 1_500 }).catch(() => undefined);
		if (await menu.isVisible().catch(() => false)) {
			return menu;
		}
		await page.waitForTimeout(150);
	}
	await expect(menu).toBeVisible();
	return menu;
}

test.describe('Public marketing smoke (desktop)', () => {
	test('emits canonical and robots metadata for public and auth routes', async ({ page }) => {
		const security = await attachSecurityGuards(page);
		await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
		await expect(page.locator('.public-site-shell[data-public-hydrated="true"]')).toBeVisible();
		await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', `${BASE_URL}/`);
		await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', 'index,follow');

		await page.goto(`${BASE_URL}/pricing`, { waitUntil: 'domcontentloaded' });
		await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
			'href',
			`${BASE_URL}/pricing`
		);
		await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', 'index,follow');

		await page.goto(`${BASE_URL}/auth/login`, { waitUntil: 'domcontentloaded' });
		await expect(page.locator('meta[name="robots"]')).toHaveAttribute(
			'content',
			'noindex,nofollow'
		);
		await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
			'href',
			`${BASE_URL}/auth/login`
		);

		for (const routeCase of [
			{
				path: '/status',
				title: /System Status \| Valdrics/i,
				description: /current service status for valdrics core platform dependencies/i
			},
			{
				path: '/privacy',
				title: /Privacy Policy \| Valdrics/i,
				description: /privacy policy covering processing scope, retention, security controls/i
			},
			{
				path: '/terms',
				title: /Terms of Service \| Valdrics/i,
				description: /terms of service covering account responsibilities, billing, acceptable use/i
			}
		]) {
			await page.goto(`${BASE_URL}${routeCase.path}`, { waitUntil: 'domcontentloaded' });
			await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
				'href',
				`${BASE_URL}${routeCase.path}`
			);
			await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', 'index,follow');
			await expect(page).toHaveTitle(routeCase.title);
			await expect(page.locator('meta[name="description"]')).toHaveAttribute(
				'content',
				routeCase.description
			);
			await expect(page.locator('script[type="application/ld+json"]').first()).toBeAttached();
		}

		await security.assertClean();
	});

	test('covers landing, pricing, docs, api docs, and status navigation', async ({
		page
	}, testInfo) => {
		await goToLanding(page);

		const landingHeading = page.getByRole('heading', { level: 1 }).first();
		await expect(landingHeading).toBeVisible();
		await expect(landingHeading).toContainText(
			/cloud|spend|governed action|owner-routed action|margin/i
		);
		await expect(page.getByRole('contentinfo')).toBeVisible();

		const primaryCta = page
			.getByRole('link', { name: /start free|book executive briefing/i })
			.first();
		await expect(primaryCta).toHaveAttribute('href', /\/auth\/login(\?.*)?$/);

		const footer = page.getByRole('contentinfo');
		await footer.getByRole('link', { name: /documentation/i }).click();
		await expect(page).toHaveURL(/\/docs$/);
		await expect(page.getByRole('heading', { level: 1, name: /documentation/i })).toBeVisible();

		const apiDocsHref = await page
			.getByRole('link', { name: /open api docs/i })
			.first()
			.getAttribute('href');
		expect(apiDocsHref || '').toMatch(/\/docs\/api$/);
		if (apiDocsHref) {
			await page.goto(new URL(apiDocsHref, BASE_URL).toString(), { waitUntil: 'domcontentloaded' });
		}
		await expect(page).toHaveURL(/\/docs\/api$/);
		await expect(page.getByRole('heading', { level: 1, name: /api reference/i })).toBeVisible();

		await page.getByRole('link', { name: /system status/i }).click();
		await expect(page).toHaveURL(/\/status$/);
		await expect(page.getByRole('heading', { level: 1, name: /system status/i })).toBeVisible();

		await page.goto(`${BASE_URL}/pricing`);
		await page.waitForLoadState('networkidle');
		await expect(
			page.getByRole('heading', { level: 1, name: /pricing that stays simple/i })
		).toBeVisible();
		const switchButton = page.getByRole('switch', { name: /toggle billing cycle/i });
		await switchButton.scrollIntoViewIfNeeded();
		await expect(switchButton).toHaveAttribute('aria-checked', 'false');
		await switchButton.click();
		await expect(switchButton).toHaveAttribute('aria-checked', 'true');
		await page.screenshot({
			path: testInfo.outputPath('desktop-public-smoke.png'),
			fullPage: true
		});
	});

	test('uses currency controls and preserves an explicit USD choice before ROI auth', async ({
		page,
		context
	}) => {
		if (isLocalDashboardUrl) {
			await context.setExtraHTTPHeaders({
				'x-vercel-ip-country': 'GB'
			});
		}
		await goToLanding(page);

		const simulatorCurrency = (await ensureInteractiveSimulator(page)).getByRole('group', {
			name: /display currency/i
		});
		await expect(simulatorCurrency).toBeVisible();
		const currencyButtons = simulatorCurrency.getByRole('button');
		const localCurrencyButton = currencyButtons.first();
		await expect(localCurrencyButton).toBeVisible();
		if (isLocalDashboardUrl) {
			await expect(localCurrencyButton).toHaveText(/local gbp/i);
		}
		const usdButton = simulatorCurrency.getByRole('button', { name: /usd/i });
		await expect(page.locator('#hero')).toContainText(/first workflow typically live/i);

		let assertedExplicitUsdPreference = false;
		if ((await currencyButtons.count()) > 1) {
			await localCurrencyButton.click();
			await expect(localCurrencyButton).toHaveAttribute('aria-pressed', 'true');
			await expect(usdButton).toBeVisible();
			await usdButton.click();
			await expect(usdButton).toHaveAttribute('aria-pressed', 'true');
			assertedExplicitUsdPreference = true;
		} else {
			await expect(localCurrencyButton).toHaveText(/usd/i);
			await expect(localCurrencyButton).toHaveAttribute('aria-pressed', 'true');
		}

		if (assertedExplicitUsdPreference) {
			await expect
				.poll(
					() =>
						page.evaluate(() => {
							return window.localStorage.getItem('valdrics_landing_currency');
						}),
					{ message: 'expected USD landing currency preference to persist in localStorage' }
				)
				.toBe('USD');
		}

		await page.goto(`${BASE_URL}/roi-planner`, { waitUntil: 'domcontentloaded' });
		await expect(page).toHaveURL(/\/auth\/login$/);
		await expect(page).toHaveTitle(/sign in/i);
		await expect(page.getByRole('heading', { level: 1, name: /welcome back/i })).toBeVisible();
		await expect(page.locator('meta[name="robots"]')).toHaveAttribute(
			'content',
			'noindex,nofollow'
		);
	});

	test('keeps public header, resources, and hero CTAs on working destinations', async ({
		page
	}) => {
		const security = await attachSecurityGuards(page);
		await goToLanding(page);
		const header = page.locator('header');

		await header.getByRole('link', { name: /^product$/i }).click();
		await assertHashDestination(page, '#product', '#product');

		await goToLanding(page);
		await header.getByRole('link', { name: /^pricing$/i }).click();
		await assertPublicRoute(page, '/pricing', /pricing that stays simple/i);

		await goToLanding(page);
		await header.getByRole('link', { name: /^enterprise$/i }).click();
		await assertPublicRoute(page, '/enterprise', /enterprise review that stays clear/i);

		await goToLanding(page);
		await (await openResourcesMenu(page))
			.getByRole('menuitem', { name: /^resource hub$/i })
			.click();
		await assertPublicRoute(page, '/resources', /resources/i);

		await goToLanding(page);
		await (await openResourcesMenu(page)).getByRole('menuitem', { name: /^docs$/i }).click();
		await assertPublicRoute(page, '/docs', /documentation/i);

		await goToLanding(page);
		await (await openResourcesMenu(page)).getByRole('menuitem', { name: /^proof pack$/i }).click();
		await assertPublicRoute(page, '/proof', /proof surfaces for buyer diligence/i);

		await goToLanding(page);
		await (await openResourcesMenu(page)).getByRole('menuitem', { name: /^about$/i }).click();
		await assertPublicRoute(page, '/about', /meet the team behind valdrics/i);

		await goToLanding(page);
		await (await openResourcesMenu(page)).getByRole('menuitem', { name: /^insights$/i }).click();
		await assertPublicRoute(page, '/insights', /insights/i);

		await goToLanding(page);
		await header
			.locator('.public-nav-secondary')
			.getByRole('link', { name: /^enterprise review$/i })
			.click();
		await assertPublicRoute(page, '/enterprise', /enterprise review that stays clear/i);

		await goToLanding(page);
		await header
			.locator('.public-nav-secondary')
			.getByRole('link', { name: /^start free$/i })
			.click();
		await expect(page).toHaveURL(/\/auth\/login(\?.*)?$/);

		await goToLanding(page);
		const hero = page.locator('#hero');
		await hero.getByRole('link', { name: /see pricing/i }).click();
		await assertPublicRoute(page, '/pricing', /pricing that stays simple/i);

		await goToLanding(page);
		await hero.getByRole('link', { name: /start free|book executive briefing/i }).click();
		await expect(page).toHaveURL(/\/auth\/login(\?.*)?$/);

		await goToLanding(page);
		await (await ensureInteractiveSimulator(page))
			.getByRole('link', { name: /open full roi planner/i })
			.click();
		await expect(page).toHaveURL(/\/auth\/login(\?.*intent=roi_assessment.*)?$/);
	});

	test('keeps proof, pricing, trust, and footer CTAs on working destinations', async ({ page }) => {
		const security = await attachSecurityGuards(page);
		await goToLanding(page);
		const simulator = await ensureInteractiveSimulator(page);
		await simulator.getByRole('link', { name: /review methodology/i }).click();
		await assertPublicRoute(
			page,
			'/docs/technical-validation',
			/public capability validation summary/i
		);

		await goToLanding(page);
		const simulatorAgain = await ensureInteractiveSimulator(page);
		const assumptionsHref = await simulatorAgain
			.locator('a[href$="valdrics-roi-assumptions.csv"]')
			.getAttribute('href');
		expect(assumptionsHref || '').toMatch(/resources\/valdrics-roi-assumptions\.csv$/);
		if (assumptionsHref) {
			await assertDownloadEndpoint(page, assumptionsHref, /text\/csv|text\/plain/i);
		}

		await goToLanding(page);
		const plans = await ensureInteractivePlans(page);
		await plans.getByRole('link', { name: /start free workspace/i }).click();
		await expect(page).toHaveURL(/\/auth\/login(\?.*plan=free.*)?$/);

		await goToLanding(page);
		await (await ensureInteractivePlans(page))
			.getByRole('link', { name: /see growth on pricing/i })
			.click();
		await assertPublicRoute(page, '/pricing', /pricing that stays simple/i);

		await goToLanding(page);
		await (await ensureInteractivePlans(page))
			.getByRole('link', { name: /review pro details/i })
			.click();
		await assertPublicRoute(page, '/pricing', /pricing that stays simple/i);

		await goToLanding(page);
		await (await ensureInteractivePlans(page))
			.getByRole('link', { name: /see detailed pricing/i })
			.click();
		await assertPublicRoute(page, '/pricing', /pricing that stays simple/i);

		await goToLanding(page);
		await (await ensureInteractivePlans(page))
			.getByRole('link', { name: /enterprise review/i })
			.click();
		await assertPublicRoute(page, '/enterprise', /enterprise review that stays clear/i);

		await goToLanding(page);
		const trust = await ensureInteractiveTrust(page);
		await trust.getByRole('link', { name: /^enterprise review$/i }).click();
		await assertPublicRoute(page, '/enterprise', /enterprise review that stays clear/i);

		await goToLanding(page);
		const onePagerHref = await (await ensureInteractiveTrust(page))
			.getByRole('link', { name: /download one-pager/i })
			.getAttribute('href');
		expect(onePagerHref || '').toMatch(/resources\/valdrics-enterprise-one-pager\.md$/);
		if (onePagerHref) {
			await assertDownloadEndpoint(page, onePagerHref, /text\/markdown|text\/plain/i);
		}

		await goToLanding(page);
		await (await ensureInteractiveTrust(page))
			.getByRole('link', { name: /request validation briefing/i })
			.click();
		await expect(page).toHaveURL(/\/talk-to-sales(\?.*)?$/);
		await expect(page).toHaveURL(/source=trust_validation/);
		await expect(page).toHaveURL(/intent=request_validation_briefing/);
		await expect(page.getByRole('heading', { level: 1, name: /talk to sales/i })).toBeVisible();

		const footerCases = [
			{ label: /documentation/i, type: 'route', path: '/docs', heading: /documentation/i },
			{
				label: /^enterprise$/i,
				type: 'route',
				path: '/enterprise',
				heading: /enterprise review that stays clear/i
			},
			{
				label: /^proof pack$/i,
				type: 'route',
				path: '/proof',
				heading: /proof surfaces for buyer diligence/i
			},
			{
				label: /^talk to sales$/i,
				type: 'route',
				path: '/talk-to-sales',
				heading: /talk to sales/i
			},
			{
				label: /^pricing$/i,
				type: 'route',
				path: '/pricing',
				heading: /pricing that stays simple/i
			},
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

		await security.assertClean();
	});

	test('public content slug routes and enterprise intake destinations stay operational', async ({
		page
	}) => {
		await assertPublicRoute(
			page,
			'/docs/quick-start-workspace',
			/quick start a valdrics workspace/i
		);
		await assertPublicRoute(page, '/resources/executive-one-pager', /executive one-pager/i);
		await assertPublicRoute(
			page,
			'/insights/from-alert-to-approved-action',
			/from alert to approved action/i
		);
		await assertPublicRoute(page, '/proof/safe-access-model', /safe access model/i);
		await assertPublicRoute(
			page,
			'/proof/deployment-and-data-residency',
			/deployment and data residency review/i
		);

		await page.goto(`${BASE_URL}/enterprise`);
		await page
			.getByRole('link', { name: /request enterprise briefing/i })
			.first()
			.click();
		await expect(page).toHaveURL(/\/talk-to-sales(\?.*)?$/);
		await expect(page.getByRole('heading', { level: 1, name: /talk to sales/i })).toBeVisible();
		await expect(page).toHaveURL(/intent=enterprise_briefing/);
	});

	test('talk-to-sales success flow submits one inquiry with marketing context', async ({
		page
	}) => {
		let capturedPayload: Record<string, unknown> | null = null;
		await page.route('**/api/marketing/talk-to-sales', async (route) => {
			capturedPayload = route.request().postDataJSON() as Record<string, unknown>;
			await route.fulfill({
				status: 202,
				contentType: 'application/json',
				body: JSON.stringify({ ok: true, accepted: true, inquiryId: 'inq-e2e-1' })
			});
		});

		await page.goto(
			`${BASE_URL}/talk-to-sales?utm_source=linkedin&utm_medium=paid&utm_campaign=q1`
		);
		await page.getByLabel(/name/i).fill('Buyer One');
		await page.getByLabel(/work email/i).fill('buyer@example.com');
		await page.getByLabel(/company/i).fill('Example Inc');
		await page.getByLabel(/role/i).fill('VP Platform');
		await page.getByLabel(/buyer region/i).selectOption('United States');
		await page.getByLabel(/cloud and saas scope/i).fill('AWS and SaaS');
		await page.getByRole('button', { name: /send inquiry/i }).click();

		await expect(page.getByRole('status')).toContainText(/inquiry received/i);
		expect(capturedPayload).toMatchObject({
			name: 'Buyer One',
			email: 'buyer@example.com',
			company: 'Example Inc',
			role: 'VP Platform',
			buyerRegion: 'United States',
			deploymentScope: 'AWS and SaaS',
			utmSource: 'linkedin',
			utmMedium: 'paid',
			utmCampaign: 'q1'
		});
	});

	test('talk-to-sales failure flow preserves inline error handling', async ({ page }) => {
		await page.route('**/api/marketing/talk-to-sales', async (route) => {
			await route.fulfill({
				status: 503,
				contentType: 'application/json',
				body: JSON.stringify({ ok: false, error: 'delivery_failed' })
			});
		});

		await page.goto(`${BASE_URL}/talk-to-sales`);
		await page.getByLabel(/name/i).fill('Buyer One');
		await page.getByLabel(/work email/i).fill('buyer@example.com');
		await page.getByLabel(/company/i).fill('Example Inc');
		await page.getByRole('button', { name: /send inquiry/i }).click();

		await expect(page.getByRole('alert')).toContainText(/could not route the inquiry/i);
	});
});

test.describe('Public marketing smoke (mobile)', () => {
	test.use({ viewport: { width: 390, height: 844 } });

	test('key landing sections and docs pages remain usable', async ({ page }, testInfo) => {
		await goToLanding(page);
		const landingHeading = page.getByRole('heading', { level: 1 }).first();
		await expect(landingHeading).toBeVisible();
		await expect(landingHeading).toContainText(
			/cloud|spend|governed action|owner-routed action|margin/i
		);
		await expect(page.locator('#product')).toBeVisible();
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
		await (await openMobileMenu(page)).getByRole('link', { name: /^enterprise review$/i }).click();
		await assertPublicRoute(page, '/enterprise', /enterprise review that stays clear/i);

		await goToLanding(page);
		await (await openMobileMenu(page)).getByRole('link', { name: /^start free$/i }).click();
		await expect(page).toHaveURL(/\/auth\/login(\?.*)?$/);

		await goToLanding(page);
		await (await openMobileMenu(page)).getByRole('link', { name: /^product$/i }).click();
		await assertHashDestination(page, '#product', '#product');

		await goToLanding(page);
		await (await openMobileMenu(page)).getByRole('link', { name: /^pricing$/i }).click();
		await assertPublicRoute(page, '/pricing', /pricing that stays simple/i);

		await goToLanding(page);
		await (await openMobileMenu(page)).getByRole('link', { name: /^enterprise$/i }).click();
		await assertPublicRoute(page, '/enterprise', /enterprise review that stays clear/i);

		await goToLanding(page);
		await (await openMobileMenu(page)).getByRole('link', { name: /^resources$/i }).click();
		await assertPublicRoute(page, '/resources', /resources/i);
	});
});
