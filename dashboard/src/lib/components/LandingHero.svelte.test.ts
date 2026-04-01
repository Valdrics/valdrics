import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import LandingHero from './LandingHero.svelte';

const LANDING_HERO_PROPS = {
	initialExperiments: {
		buyerPersonaDefault: 'cto',
		heroVariant: 'control_every_dollar',
		ctaVariant: 'start_free',
		sectionOrderVariant: 'problem_first',
		seed: 'default'
	},
	includeExperimentQueryParams: false,
	initialMotionProfile: 'subtle',
	canonicalUrl: 'https://example.com/',
	ogImageUrl: 'https://example.com/og-image.png',
	detectedCurrencyCode: 'USD',
	buyerPersonaId: 'cto',
	heroPrimaryIntent: 'engineering_control',
	heroTitle: 'Control cloud spend without slowing delivery.',
	heroSubtitle:
		'Valdrics gives finance and engineering one workflow for triage, approval, execution, and savings proof.',
	initialSnapshot: {
		id: 'snp-2026-02-27-a',
		label: 'Snapshot A',
		capturedAt: '2026-02-27T20:55:58Z',
		traceId: 'trace-snapshot-a',
		lanes: [
			{
				id: 'economic_visibility',
				status: 'Watch',
				severity: 'watch',
				wasteUsd: 12400,
				actionLabel: 'Assign Owner'
			},
			{ id: 'deterministic_enforcement', status: 'Stable', severity: 'healthy' },
			{ id: 'financial_governance', status: 'Stable', severity: 'healthy' },
			{ id: 'operational_resilience', status: 'Stable', severity: 'healthy' }
		],
		sources: ['Cloud cost telemetry', 'Failure drill evidence', 'Execution coverage report']
	}
} as const;

vi.mock('$env/dynamic/public', () => ({
	env: {
		PUBLIC_API_URL: 'https://example.com/api/v1'
	}
}));

vi.mock('$app/paths', () => ({
	base: ''
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

		render(LandingHero, LANDING_HERO_PROPS);

		expect(
			screen.getByRole('heading', {
				level: 1,
				name: /control cloud spend without slowing delivery|move from spend reports to accountable action|review spend-changing actions with context|protect margin with clearer spend decisions/i
			})
		).toBeTruthy();
		expect(
			await screen.findByRole('heading', {
				name: /replace reactive cleanup with one operating path/i
			})
		).toBeTruthy();
		expect(
			await screen.findByRole('heading', { name: /model the savings case in minutes/i })
		).toBeTruthy();
		expect(
			await screen.findByRole('heading', { name: /pricing that matches rollout stage/i })
		).toBeTruthy();
		expect(
			await screen.findByRole('heading', { name: /review the company before you talk to us/i })
		).toBeTruthy();

		const currencyGroups = await screen.findAllByRole('group', { name: /display currency/i });
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
		render(LandingHero, LANDING_HERO_PROPS);

		expect(await screen.findByRole('dialog', { name: /cookie preferences/i })).toBeTruthy();
		const declineButton = screen.getByRole('button', { name: /decline analytics/i });
		await fireEvent.click(declineButton);
		expect(window.localStorage.getItem('valdrics.cookie_consent.v1')).toBe('rejected');
	});

	it('renders a real dashboard still with concise proof notes', () => {
		render(LandingHero, LANDING_HERO_PROPS);

		expect(screen.getByRole('img', { name: /real valdrics dashboard/i })).toBeTruthy();
		const productStill = within(screen.getByLabelText(/real product dashboard screenshot/i));
		expect(
			productStill.getByText(/real workspace still from the signed-in dashboard/i)
		).toBeTruthy();
		expect(productStill.getByText(/^decision record$/i)).toBeTruthy();
		expect(productStill.getByText(/^current stage$/i)).toBeTruthy();
		expect(productStill.getByText(/^linked proof$/i)).toBeTruthy();
	});

	it('disables auto-rotation when reduced motion is preferred', async () => {
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

		const { unmount } = render(LandingHero, LANDING_HERO_PROPS);
		await Promise.resolve();
		await Promise.resolve();
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

	it('cleans rotating intervals on unmount for concurrency safety', async () => {
		vi.useFakeTimers();
		const setIntervalSpy = vi.spyOn(globalThis, 'setInterval');
		const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval');

		const { unmount } = render(LandingHero, LANDING_HERO_PROPS);
		await waitFor(() => {
			expect(setIntervalSpy).toHaveBeenCalled();
		});

		unmount();
		expect(clearIntervalSpy).toHaveBeenCalled();

		setIntervalSpy.mockRestore();
		clearIntervalSpy.mockRestore();
		vi.useRealTimers();
	});
});
