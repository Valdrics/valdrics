import { mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const __dirname = dirname(fileURLToPath(import.meta.url));

const outputPath = resolve(
	process.env.HERO_STILL_OUTPUT_PATH || resolve(__dirname, '../static/landing-dashboard-still.jpg')
);
const pageUrl =
	process.env.HERO_STILL_SOURCE_URL || 'http://127.0.0.1:5174/__capture/dashboard-hero';
const viewportWidth = Number(process.env.HERO_STILL_VIEWPORT_WIDTH || '1440');
const viewportHeight = Number(process.env.HERO_STILL_VIEWPORT_HEIGHT || '960');

const browser = await chromium.launch({
	headless: true
});

try {
	const context = await browser.newContext({
		viewport: { width: viewportWidth, height: viewportHeight },
		deviceScaleFactor: 1
	});
	const page = await context.newPage();

	await page.emulateMedia({ reducedMotion: 'reduce' });
	await page.goto(pageUrl, {
		waitUntil: 'domcontentloaded'
	});
	await page.waitForLoadState('networkidle');
	await page.getByRole('heading', { level: 1, name: /dashboard/i }).waitFor({
		state: 'visible',
		timeout: 30_000
	});
	await page.waitForTimeout(450);

	const captureTarget = page.locator('[data-dashboard-hero-capture]');
	await captureTarget.waitFor({
		state: 'visible',
		timeout: 30_000
	});

	await mkdir(dirname(outputPath), { recursive: true });
	await captureTarget.screenshot({
		path: outputPath,
		type: 'jpeg',
		quality: 88,
		animations: 'disabled',
		caret: 'hide'
	});
} finally {
	await browser.close();
}
