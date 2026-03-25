import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import LandingHero from './LandingHero.svelte';

vi.mock('$env/dynamic/public', () => ({
	env: {
		PUBLIC_API_URL: 'https://example.com/api/v1'
	}
}));

vi.mock('$app/paths', () => ({
	assets: '',
	base: ''
}));

vi.mock('$app/stores', () => ({
	page: readable({
		url: new URL('https://example.com/')
	})
}));

afterEach(() => {
	cleanup();
	window.localStorage.clear();
	delete (window as Window & { dataLayer?: unknown[] }).dataLayer;
});

describe('LandingHero', () => {
	it('renders the current landing narrative with local-vs-USD ROI controls', async () => {
		const dataLayer: unknown[] = [];
		(window as Window & { dataLayer?: unknown[] }).dataLayer = dataLayer;
		window.localStorage.setItem('valdrics.cookie_consent.v1', 'accepted');

		render(LandingHero);

		expect(
			screen.getByRole('heading', {
				level: 1,
				name: /control cloud spend without slowing delivery|move from spend reports to accountable action|review spend-changing actions with context|protect margin with clearer spend decisions/i
			})
		).toBeTruthy();
		expect(
			screen.getByRole('heading', { name: /replace reactive cleanup with one operating path/i })
		).toBeTruthy();
		expect(
			screen.getByRole('heading', { name: /model the savings case in minutes/i })
		).toBeTruthy();
		expect(
			screen.getByRole('heading', { name: /pricing that matches rollout stage/i })
		).toBeTruthy();
		expect(
			screen.getByRole('heading', { name: /review the company before you talk to us/i })
		).toBeTruthy();

		const currencyGroups = screen.getAllByRole('group', { name: /display currency/i });
		expect(currencyGroups.length).toBeGreaterThanOrEqual(1);
		const firstCurrencyGroup = within(currencyGroups[0]!);
		expect(firstCurrencyGroup.getAllByRole('button').length).toBeGreaterThanOrEqual(1);
		expect(
			firstCurrencyGroup
				.getAllByRole('button')
				.some((button) => button.getAttribute('aria-pressed') === 'true')
		).toBe(true);

		expect(screen.queryByText(/prelaunch, with honest public review surfaces/i)).toBeNull();
		expect(screen.getAllByRole('link', { name: /about \/ team/i }).length).toBeGreaterThan(0);
		const enterpriseReviewLinks = screen.getAllByRole('link', { name: /^enterprise review$/i });
		expect(enterpriseReviewLinks.length).toBeGreaterThan(0);
		expect(enterpriseReviewLinks[0]?.getAttribute('href') || '').toContain('/enterprise?');

		await fireEvent.click(
			screen.getAllByRole('link', { name: /start free workspace|book executive briefing/i })[0]!
		);
		await waitFor(() => {
			expect(dataLayer.length).toBeGreaterThan(0);
		});
		const payload = dataLayer[dataLayer.length - 1] as Record<string, unknown>;
		expect(payload.event).toBe('valdrics_landing_event');
	});

	it('shows cookie consent controls before analytics is accepted', async () => {
		window.localStorage.removeItem('valdrics.cookie_consent.v1');
		render(LandingHero);

		expect(await screen.findByRole('dialog', { name: /cookie preferences/i })).toBeTruthy();
		const declineButton = screen.getByRole('button', { name: /decline analytics/i });
		await fireEvent.click(declineButton);
		expect(window.localStorage.getItem('valdrics.cookie_consent.v1')).toBe('rejected');
	});

	it('renders a real dashboard still with concise proof notes', () => {
		render(LandingHero);

		expect(screen.getByRole('img', { name: /real valdrics dashboard/i })).toBeTruthy();
		const productStill = within(screen.getByLabelText(/real product dashboard screenshot/i));
		expect(
			productStill.getByText(/real workspace still from the signed-in dashboard/i)
		).toBeTruthy();
		expect(productStill.getByText(/^decision record$/i)).toBeTruthy();
		expect(productStill.getByText(/^current stage$/i)).toBeTruthy();
		expect(productStill.getByText(/^linked proof$/i)).toBeTruthy();
	});

	it('disables auto-rotation when reduced motion is preferred', () => {
		vi.useFakeTimers();
		const setIntervalSpy = vi.spyOn(globalThis, 'setInterval');
		const originalMatchMedia = window.matchMedia;
		const matchMediaStub = vi.fn().mockReturnValue({
			matches: true,
			addEventListener: vi.fn(),
			removeEventListener: vi.fn()
		});
		Object.defineProperty(window, 'matchMedia', {
			writable: true,
			value: matchMediaStub
		});

		const { unmount } = render(LandingHero);
		const intervalDurationsMs = setIntervalSpy.mock.calls.map((call) => Number(call[1]));
		expect(intervalDurationsMs).not.toContain(4400);
		expect(intervalDurationsMs).not.toContain(3200);

		unmount();
		setIntervalSpy.mockRestore();
		Object.defineProperty(window, 'matchMedia', {
			writable: true,
			value: originalMatchMedia
		});
		vi.useRealTimers();
	});

	it('cleans rotating intervals on unmount for concurrency safety', () => {
		vi.useFakeTimers();
		const setIntervalSpy = vi.spyOn(globalThis, 'setInterval');
		const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval');

		const { unmount } = render(LandingHero);
		expect(setIntervalSpy).toHaveBeenCalled();

		unmount();
		expect(clearIntervalSpy).toHaveBeenCalled();

		setIntervalSpy.mockRestore();
		clearIntervalSpy.mockRestore();
		vi.useRealTimers();
	});
});
