import { describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import LandingHeroView from './LandingHeroView.svelte';
import { CLOUD_HOOK_STATES } from '$lib/landing/heroContent.core';
import { REALTIME_SIGNAL_SNAPSHOTS } from '$lib/landing/realtimeSignalMap';

vi.mock('$app/paths', () => ({
	assets: '',
	base: ''
}));

function buildProps(sectionOrderVariant: 'problem_first' | 'workflow_first') {
	const activeSnapshot = REALTIME_SIGNAL_SNAPSHOTS[0];
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
		secondaryCtaHref: '/pricing?entry=hero_secondary',
		primaryCtaHref: '/auth/login?intent=engineering_control',
		secondaryCtaTelemetryValue: 'see_pricing',
		ctaVariant: 'start_free' as const,
		sectionOrderVariant,
		cloudHookStates: CLOUD_HOOK_STATES,
		activeHookState: CLOUD_HOOK_STATES[0],
		hookStateIndex: 0,
		onSelectHookState: vi.fn(),
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
		currencyCode: 'USD',
		onTrackScenarioAdjust: vi.fn(),
		onScenarioWasteWithoutChange: vi.fn(),
		onScenarioWasteWithChange: vi.fn(),
		onScenarioWindowChange: vi.fn(),
		roiPlannerHref: '/auth/login?intent=roi_assessment',
		freeTierCtaHref: '/pricing?plan=free',
		buildPlanCtaHref: (planId: string) => `/pricing?plan=${planId}`,
		plansTalkToSalesHref: '/talk-to-sales',
		plansEnterpriseHref: '/enterprise?source=plans_enterprise',
		trustEnterpriseHref: '/enterprise?source=trust_enterprise',
		requestValidationBriefingHref: '/talk-to-sales?source=trust_validation',
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

function storyBandOrder(container: HTMLElement): string[] {
	const storyBand = container.querySelector('.landing-story-band');
	if (!(storyBand instanceof HTMLElement)) {
		throw new Error('missing story band');
	}
	return Array.from(storyBand.children).map(
		(element) =>
			element.id || element.getAttribute('data-landing-section') || element.tagName.toLowerCase()
	);
}

describe('LandingHeroView', () => {
	it('renders product narrative before workflow map for problem-first experiments', () => {
		const view = render(LandingHeroView, {
			props: buildProps('problem_first')
		});

		expect(storyBandOrder(view.container)).toEqual([
			'product',
			'signal-map',
			'simulator',
			'plans',
			'trust'
		]);
	});

	it('renders workflow map before product narrative for workflow-first experiments', () => {
		const view = render(LandingHeroView, {
			props: buildProps('workflow_first')
		});

		expect(storyBandOrder(view.container)).toEqual([
			'signal-map',
			'product',
			'simulator',
			'plans',
			'trust'
		]);
	});
});
