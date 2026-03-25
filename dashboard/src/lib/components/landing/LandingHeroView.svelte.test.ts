import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/svelte';
import LandingHeroView from './LandingHeroView.svelte';
import type { LandingCurrencyCode } from '$lib/landing/currencyPreference';
import { CLOUD_HOOK_STATES } from '$lib/landing/heroContent.core';
import { LANDING_SIGNAL_SNAPSHOTS } from '$lib/landing/landingSignalSnapshots';

vi.mock('$app/paths', () => ({
	assets: '',
	base: ''
}));

afterEach(() => {
	cleanup();
});

function buildProps() {
	const activeSnapshot = LANDING_SIGNAL_SNAPSHOTS[0];
	const activeSignalLane = activeSnapshot?.lanes[0];
	if (!activeSnapshot || !activeSignalLane) {
		throw new Error('expected realtime signal snapshot fixture');
	}

	return {
		motionProfile: 'subtle' as const,
		landingScrollProgressPct: 25,
		canonicalUrl: 'https://www.example.com',
		imageUrl: 'https://www.example.com/og.png',
		heroTitle: 'Control cloud spend decisions.',
		heroSubtitle: 'Route signals to owners and record outcomes.',
		primaryCtaLabel: 'Start Free Workspace',
		secondaryCtaLabel: 'See Pricing',
		secondaryCtaHref: '/pricing?source=hero_secondary',
		primaryCtaHref: '/auth/login?intent=engineering_control',
		secondaryCtaTelemetryValue: 'see_pricing',
		cloudHookStates: CLOUD_HOOK_STATES,
		activeSnapshot,
		activeSignalLane,
		signalMapInView: true,
		snapshotIndex: 0,
		demoStepIndex: 0,
		onSelectSignalLane: vi.fn(),
		onSelectDemoStep: vi.fn(),
		onSelectSnapshot: vi.fn(),
		onSignalMapElementChange: vi.fn(),
		normalizedScenarioWasteWithoutPct: 18,
		normalizedScenarioWasteWithPct: 7,
		normalizedScenarioWindowMonths: 12,
		scenarioWithoutBarPct: 100,
		scenarioWithBarPct: 40,
		scenarioWasteWithoutUsd: 21600,
		scenarioWasteWithUsd: 8400,
		scenarioWasteRecoveryMonthlyUsd: 13200,
		scenarioWasteRecoveryWindowUsd: 158400,
		monthlySpendUsd: 120000,
		scenarioWasteWithoutPct: 18,
		scenarioWasteWithPct: 7,
		scenarioWindowMonths: 12,
		formatUsd: (amount: number) => `$${amount.toFixed(0)}`,
		localCurrencyCode: 'USD' as LandingCurrencyCode,
		currencyCode: 'USD' as LandingCurrencyCode,
		onCurrencyCodeChange: vi.fn(),
		onTrackScenarioAdjust: vi.fn(),
		onScenarioWasteWithoutChange: vi.fn(),
		onScenarioWasteWithChange: vi.fn(),
		onScenarioWindowChange: vi.fn(),
		roiPlannerHref: '/auth/login?intent=roi_assessment',
		freeTierCtaHref: '/pricing?plan=free',
		buildPlanCtaHref: (planId: string) => `/pricing?plan=${planId}`,
		trustEnterpriseHref: '/enterprise?source=trust_enterprise',
		aboutHref: '/about?source=trust_about',
		docsHref: '/docs?source=trust_docs',
		statusHref: '/status?source=trust_status',
		proofHref: '/proof?source=trust_proof',
		requestValidationBriefingHref:
			'/talk-to-sales?source=trust_validation&intent=request_validation_briefing',
		onePagerHref: '/resources/one-pager.md',
		subscribeApiPath: '/api/marketing/subscribe',
		resourcesHref: '/resources',
		onTrackCta: vi.fn(),
		cookieBannerVisible: false,
		onSetTelemetryConsent: vi.fn(),
		onCloseCookieBanner: vi.fn(),
		onOpenCookieSettings: vi.fn(),
		showBackToTop: false
	};
}

describe('LandingHeroView', () => {
	it('renders the fixed landing narrative order', () => {
		const view = render(LandingHeroView, {
			props: buildProps()
		});

		const sectionIds = Array.from(view.container.querySelectorAll('section[id]')).map(
			(element) => element.id
		);
		expect(sectionIds).toEqual(['hero', 'product', 'simulator', 'plans', 'trust']);
	});

	it('renders the trust section with proof and human-proof links wired', () => {
		const view = render(LandingHeroView, {
			props: buildProps()
		});

		const trustSection = view.container.querySelector('#trust');
		expect(trustSection).toBeTruthy();
		expect(trustSection?.textContent || '').toContain('Review the company before you talk to us');
		expect(
			(trustSection?.querySelector('a[href*="/proof"]') as HTMLAnchorElement | null)?.href || ''
		).toContain('/proof');
		expect(
			(trustSection?.querySelector('a[href*="/about"]') as HTMLAnchorElement | null)?.href || ''
		).toContain('/about');
	});

	it('renders the hero with a real dashboard still instead of the old synthetic mockup', () => {
		const view = render(LandingHeroView, {
			props: buildProps()
		});

		const heroScreenshot = view.container.querySelector(
			'img[src*="landing-dashboard-still.jpg"]'
		) as HTMLImageElement | null;
		expect(heroScreenshot).toBeTruthy();
		expect(heroScreenshot?.alt || '').toContain('Real Valdrics dashboard');
		expect(view.container.textContent || '').toContain(
			'Real workspace still from the signed-in dashboard.'
		);
	});
});
