<script lang="ts">
	import { browser } from '$app/environment';
	import { assets, base } from '$app/paths';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import {
		REALTIME_SIGNAL_SNAPSHOTS,
		nextSnapshotIndex,
		type SignalLaneId
	} from '$lib/landing/realtimeSignalMap';
	import {
		resolveLandingExperiments,
		shouldIncludeExperimentQueryParams,
		type LandingExperimentAssignments
	} from '$lib/landing/landingExperiment';
	import type { LandingAttribution } from '$lib/landing/landingFunnel';
	import {
		DEFAULT_EXPERIMENT_ASSIGNMENTS,
		DEMO_ROTATION_MS,
		GEO_CURRENCY_HINT_TIMEOUT_MS,
		LANDING_CONSENT_KEY,
		LANDING_SCROLL_MILESTONES,
		resolveLandingMotionProfile,
		SNAPSHOT_ROTATION_MS
	} from '$lib/landing/landingHeroConfig';
	import {
		buildLandingHeroSalesPath,
		buildLandingHeroSignupPath,
		trackIndexedLandingSelection
	} from '$lib/landing/landingHeroActions';
	import { mountLandingHeroBrowserRuntime } from '$lib/landing/landingHeroBrowserRuntime';
	import { createLandingHeroTelemetryBridge } from '$lib/landing/landingHeroTelemetryBridge';
	import {
		calculateLandingHeroScenarioMetrics,
		formatLandingHeroCurrencyAmount,
		resolveLandingHeroCurrencyCode
	} from '$lib/landing/landingHeroScenario';
	import {
		DEFAULT_LANDING_ROI_INPUTS,
		normalizeLandingRoiInputs
	} from '$lib/landing/roiCalculator';
	import { getReducedMotionPreference } from '$lib/landing/reducedMotion';
	import {
		BUYER_ROLE_VIEWS,
		CLOUD_HOOK_STATES,
		HERO_ROLE_CONTEXT,
		MICRO_DEMO_STEPS
	} from '$lib/landing/heroContent';
	import LandingHeroView from '$lib/components/landing/LandingHeroView.svelte';
	import './LandingHero.css';
	const GEO_CURRENCY_HINT_ENDPOINT = `${base}/api/geo/currency`;
	const DEFAULT_SIGNAL_SNAPSHOT = REALTIME_SIGNAL_SNAPSHOTS[0];
	const ONE_PAGER_HREF = `${base}/resources/valdrics-enterprise-one-pager.md`,
		RESOURCES_PATH = `${base}/resources`;
	const SUBSCRIBE_API_PATH = `${base}/api/marketing/subscribe`,
		TALK_TO_SALES_PATH = `${base}/talk-to-sales`,
		ENTERPRISE_PATH = `${base}/enterprise`;
	if (!DEFAULT_SIGNAL_SNAPSHOT)
		throw new Error('Realtime signal map requires at least one snapshot.');
	let signalMapElement: HTMLDivElement | null = null;
	let signalMapInView = $state(true),
		documentVisible = $state(true),
		snapshotIndex = $state(0),
		hookStateIndex = $state(0),
		buyerRoleIndex = $state(0),
		demoStepIndex = $state(0);
	let activeLaneId = $state<SignalLaneId | null>(null),
		visitorId = $state(''),
		pageReferrer = $state('');
	let experiments = $state<LandingExperimentAssignments>(
		resolveLandingExperiments($page.url, DEFAULT_EXPERIMENT_ASSIGNMENTS.seed)
	);
	let attribution = $state<LandingAttribution>({ utm: {} }),
		engagedCaptured = $state(false);
	let roiMonthlySpendUsd = $state(DEFAULT_LANDING_ROI_INPUTS.monthlySpendUsd),
		roiExpectedReductionPct = $state(DEFAULT_LANDING_ROI_INPUTS.expectedReductionPct),
		roiRolloutDays = $state(DEFAULT_LANDING_ROI_INPUTS.rolloutDays);
	let roiTeamMembers = $state(DEFAULT_LANDING_ROI_INPUTS.teamMembers),
		roiBlendedHourlyUsd = $state(DEFAULT_LANDING_ROI_INPUTS.blendedHourlyUsd),
		roiPlatformAnnualCostUsd = $state(DEFAULT_LANDING_ROI_INPUTS.platformAnnualCostUsd);
	let scenarioWasteWithoutPct = $state(18),
		scenarioWasteWithPct = $state(7),
		scenarioWindowMonths = $state(12),
		scenarioAdjustCaptured = $state(false),
		landingScrollProgressPct = $state(0);
	let prefersReducedMotion = $state(
		getReducedMotionPreference(browser && typeof window !== 'undefined' ? window : undefined)
	);
	let telemetryEnabled = $state(false),
		telemetryInitialized = $state(false),
		cookieBannerVisible = $state(false),
		roiCurrencyCode = $state('USD');
	let activeSnapshot = $derived(
		REALTIME_SIGNAL_SNAPSHOTS[snapshotIndex] ?? DEFAULT_SIGNAL_SNAPSHOT
	);
	let activeHookState = $derived(CLOUD_HOOK_STATES[hookStateIndex] ?? CLOUD_HOOK_STATES[0]);
	let activeBuyerRole = $derived(BUYER_ROLE_VIEWS[buyerRoleIndex] ?? BUYER_ROLE_VIEWS[0]);
	let activeSignalLane = $derived(
		activeSnapshot.lanes.find((lane) => lane.id === activeLaneId) ?? activeSnapshot.lanes[0]
	);
	let heroContext = $derived(HERO_ROLE_CONTEXT[activeBuyerRole.id] ?? HERO_ROLE_CONTEXT.finops);
	let heroTitle = $derived(
		experiments.heroVariant === 'from_metrics_to_control'
			? heroContext.metricsTitle
			: heroContext.controlTitle
	);
	let heroSubtitle = $derived(heroContext.subtitle);
	let canonicalUrl = $derived(new URL($page.url.pathname, $page.url.origin).toString()),
		ogImageUrl = $derived(new URL(`${assets}/og-image.png`, $page.url.origin).toString());
	let primaryCtaLabel = $derived(
		experiments.ctaVariant === 'book_briefing' ? 'Book Executive Briefing' : 'Start Free Workspace'
	);
	let secondaryCtaLabel = $derived('See Pricing'),
		secondaryCtaHref = $derived('/pricing?entry=hero_secondary');
	let roiPlannerHref = $derived(buildSignupHref('roi_assessment', { source: 'simulator' }));
	let plansTalkToSalesHref = $derived(buildTalkToSalesHref('plans')),
		requestValidationBriefingHref = $derived(buildTalkToSalesHref('trust_validation')),
		plansEnterpriseHref = $derived(buildEnterpriseReviewHref('plans_enterprise')),
		trustEnterpriseHref = $derived(buildEnterpriseReviewHref('trust_enterprise'));
	let showBackToTop = $derived(landingScrollProgressPct >= 8),
		motionProfile = $derived(resolveLandingMotionProfile($page.url));
	let primaryCtaIntent = $derived(
		experiments.ctaVariant === 'book_briefing' ? 'executive_briefing' : heroContext.primaryIntent
	);
	let primaryCtaHref = $derived(
		experiments.ctaVariant === 'book_briefing'
			? buildTalkToSalesHref('hero_briefing')
			: buildSignupHref(primaryCtaIntent)
	);
	let freeTierCtaHref = $derived(
		buildSignupHref('free_tier', { plan: 'free', source: 'free_tier' })
	);
	let secondaryCtaTelemetryValue = $derived('see_pricing');
	let includeExperimentQueryParams = $derived(shouldIncludeExperimentQueryParams($page.url, false));
	let shouldRotateSnapshots = $derived(
		!prefersReducedMotion &&
			documentVisible &&
			signalMapInView &&
			REALTIME_SIGNAL_SNAPSHOTS.length > 1
	);
	let shouldRotateDemoSteps = $derived(
		!prefersReducedMotion && documentVisible && MICRO_DEMO_STEPS.length > 1
	);
	let roiInputs = $derived(
		normalizeLandingRoiInputs({
			monthlySpendUsd: roiMonthlySpendUsd,
			expectedReductionPct: roiExpectedReductionPct,
			rolloutDays: roiRolloutDays,
			teamMembers: roiTeamMembers,
			blendedHourlyUsd: roiBlendedHourlyUsd,
			platformAnnualCostUsd: roiPlatformAnnualCostUsd
		})
	);
	let scenarioMetrics = $derived(
		calculateLandingHeroScenarioMetrics({
			monthlySpendUsd: roiInputs.monthlySpendUsd,
			wasteWithoutPct: scenarioWasteWithoutPct,
			wasteWithPct: scenarioWasteWithPct,
			windowMonths: scenarioWindowMonths
		})
	);
	$effect(() => {
		const defaultBuyerIndex = BUYER_ROLE_VIEWS.findIndex(
			(role) => role.id === experiments.buyerPersonaDefault
		);
		if (defaultBuyerIndex >= 0) {
			buyerRoleIndex = defaultBuyerIndex;
		}
	});
	$effect(() => {
		if (!activeSignalLane && activeSnapshot.lanes[0]) {
			activeLaneId = activeSnapshot.lanes[0].id;
			return;
		}
		// Auto-synchronize focus during rotation
		if (shouldRotateSnapshots) {
			const watchLane = activeSnapshot.lanes.find(
				(lane) => lane.severity === 'watch' || lane.severity === 'critical'
			);
			if (watchLane && watchLane.id !== activeLaneId) {
				activeLaneId = watchLane.id;
			}
		}
	});
	$effect(() => {
		if (!shouldRotateSnapshots) return;
		const interval = setInterval(() => {
			snapshotIndex = nextSnapshotIndex(snapshotIndex, REALTIME_SIGNAL_SNAPSHOTS.length);
		}, SNAPSHOT_ROTATION_MS);
		return () => clearInterval(interval);
	});
	$effect(() => {
		if (!shouldRotateDemoSteps) return;
		const interval = setInterval(() => {
			demoStepIndex = nextSnapshotIndex(demoStepIndex, MICRO_DEMO_STEPS.length);
		}, DEMO_ROTATION_MS);
		return () => clearInterval(interval);
	});
	onMount(() =>
		mountLandingHeroBrowserRuntime({
			browserEnabled: browser,
			windowRef: window,
			documentRef: document,
			signalMapElement,
			geoCurrencyHintTimeoutMs: GEO_CURRENCY_HINT_TIMEOUT_MS,
			applyGeoCurrencyHint,
			consentStorageKey: LANDING_CONSENT_KEY,
			scrollMilestones: LANDING_SCROLL_MILESTONES,
			initializeTelemetry: initialize,
			markEngaged,
			buildTelemetryContext,
			emitLandingTelemetrySafe,
			setPrefersReducedMotion: (value) => (prefersReducedMotion = value),
			setPageReferrer: (value) => (pageReferrer = value),
			setTelemetryEnabled: (value) => (telemetryEnabled = value),
			setCookieBannerVisible: (value) => (cookieBannerVisible = value),
			setDocumentVisible: (value) => (documentVisible = value),
			setSignalMapInView: (value) => (signalMapInView = value),
			setLandingScrollProgressPct: (value) => (landingScrollProgressPct = value)
		})
	);
	const telemetry = createLandingHeroTelemetryBridge({
		getTelemetryEnabled: () => telemetryEnabled,
		setTelemetryEnabled: (value) => (telemetryEnabled = value),
		getTelemetryInitialized: () => telemetryInitialized,
		setTelemetryInitialized: (value) => (telemetryInitialized = value),
		setCookieBannerVisible: (value) => (cookieBannerVisible = value),
		getEngagedCaptured: () => engagedCaptured,
		setEngagedCaptured: (value) => (engagedCaptured = value),
		getScenarioAdjustCaptured: () => scenarioAdjustCaptured,
		setScenarioAdjustCaptured: (value) => (scenarioAdjustCaptured = value),
		getVisitorId: () => visitorId,
		setVisitorId: (value) => (visitorId = value),
		getExperiments: () => experiments,
		setExperiments: (value) => (experiments = value),
		getAttribution: () => attribution,
		setAttribution: (value) => (attribution = value),
		getPersona: () => activeBuyerRole.id,
		getPagePath: () => $page.url.pathname,
		getReferrer: () => pageReferrer,
		getStorage: () => (browser ? window.localStorage : undefined),
		getPageUrl: () => $page.url,
		consentStorageKey: LANDING_CONSENT_KEY
	});
	const {
		buildTelemetryContext,
		emitLandingTelemetrySafe,
		markEngaged,
		initialize,
		setTelemetryConsent,
		trackCta,
		trackScenarioAdjust
	} = telemetry;
	const closeCookieBanner = () => (cookieBannerVisible = false),
		openCookieSettings = () => (cookieBannerVisible = true);
	function buildSignupHref(intent: string, extraParams: Record<string, string> = {}): string {
		return buildLandingHeroSignupPath({
			basePath: base,
			intent,
			persona: activeBuyerRole.id,
			includeExperimentQueryParams,
			experiments,
			utm: attribution.utm,
			extraParams
		});
	}
	function buildPlanCtaHref(planId: string): string {
		return buildSignupHref('start_plan', { plan: planId, source: 'plans' });
	}
	function buildTalkToSalesHref(source: string): string {
		return buildLandingHeroSalesPath({
			path: TALK_TO_SALES_PATH,
			source,
			persona: activeBuyerRole.id,
			utm: attribution.utm
		});
	}
	function buildEnterpriseReviewHref(source: string): string {
		return buildLandingHeroSalesPath({
			path: ENTERPRISE_PATH,
			source,
			persona: activeBuyerRole.id,
			utm: attribution.utm
		});
	}
	const selectSnapshot = (index: number) =>
		trackIndexedLandingSelection({
			index,
			size: REALTIME_SIGNAL_SNAPSHOTS.length,
			assign: (value) => (snapshotIndex = value),
			eventName: 'snapshot_select',
			section: 'signal_map',
			value: REALTIME_SIGNAL_SNAPSHOTS[index]?.id,
			markEngaged,
			emitLandingTelemetrySafe,
			buildTelemetryContext
		});
	const selectHookState = (index: number) =>
		trackIndexedLandingSelection({
			index,
			size: CLOUD_HOOK_STATES.length,
			assign: (value) => (hookStateIndex = value),
			eventName: 'hook_toggle',
			section: 'cloud_hook',
			value: CLOUD_HOOK_STATES[index]?.id,
			markEngaged,
			emitLandingTelemetrySafe,
			buildTelemetryContext
		});
	const selectDemoStep = (index: number) =>
		trackIndexedLandingSelection({
			index,
			size: MICRO_DEMO_STEPS.length,
			assign: (value) => (demoStepIndex = value),
			eventName: 'micro_demo_step',
			section: 'hero_demo',
			value: MICRO_DEMO_STEPS[index]?.id,
			markEngaged,
			emitLandingTelemetrySafe,
			buildTelemetryContext
		});
	const selectSignalLane = (laneId: SignalLaneId): void => {
		activeLaneId = laneId;
		markEngaged();
		emitLandingTelemetrySafe('lane_focus', 'signal_map', laneId, buildTelemetryContext('engaged'));
	};
	const handleSignalMapElementChange = (element: HTMLDivElement | null) =>
		(signalMapElement = element);
	const handleScenarioWasteWithoutChange = (value: number) => (scenarioWasteWithoutPct = value);
	const handleScenarioWasteWithChange = (value: number) => (scenarioWasteWithPct = value);
	const handleScenarioWindowChange = (value: number) => (scenarioWindowMonths = value);
	const formatUsd = (amount: number, currency: string = roiCurrencyCode) =>
		formatLandingHeroCurrencyAmount(amount, currency);
	async function applyGeoCurrencyHint(signal: AbortSignal): Promise<void> {
		roiCurrencyCode = await resolveLandingHeroCurrencyCode({
			requestEndpoint: GEO_CURRENCY_HINT_ENDPOINT,
			requestOrigin: $page.url.origin,
			hostname: browser && typeof window !== 'undefined' ? window.location.hostname : undefined,
			signal
		});
	}
</script>

<LandingHeroView
	{motionProfile}
	{landingScrollProgressPct}
	{canonicalUrl}
	imageUrl={ogImageUrl}
	{heroTitle}
	{heroSubtitle}
	{primaryCtaLabel}
	{secondaryCtaLabel}
	{secondaryCtaHref}
	{primaryCtaHref}
	{secondaryCtaTelemetryValue}
	ctaVariant={experiments.ctaVariant}
	sectionOrderVariant={experiments.sectionOrderVariant}
	cloudHookStates={CLOUD_HOOK_STATES}
	{activeHookState}
	{hookStateIndex}
	onSelectHookState={selectHookState}
	{activeSnapshot}
	{activeSignalLane}
	{signalMapInView}
	{snapshotIndex}
	{demoStepIndex}
	onSelectSignalLane={selectSignalLane}
	onSelectDemoStep={selectDemoStep}
	onSelectSnapshot={selectSnapshot}
	onSignalMapElementChange={handleSignalMapElementChange}
	normalizedScenarioWasteWithoutPct={scenarioMetrics.normalizedScenarioWasteWithoutPct}
	normalizedScenarioWasteWithPct={scenarioMetrics.normalizedScenarioWasteWithPct}
	normalizedScenarioWindowMonths={scenarioMetrics.normalizedScenarioWindowMonths}
	scenarioWithoutBarPct={scenarioMetrics.scenarioWithoutBarPct}
	scenarioWithBarPct={scenarioMetrics.scenarioWithBarPct}
	scenarioWasteWithoutUsd={scenarioMetrics.scenarioWasteWithoutUsd}
	scenarioWasteWithUsd={scenarioMetrics.scenarioWasteWithUsd}
	scenarioWasteRecoveryMonthlyUsd={scenarioMetrics.scenarioWasteRecoveryMonthlyUsd}
	scenarioWasteRecoveryWindowUsd={scenarioMetrics.scenarioWasteRecoveryWindowUsd}
	monthlySpendUsd={roiInputs.monthlySpendUsd}
	{scenarioWasteWithoutPct}
	{scenarioWasteWithPct}
	{scenarioWindowMonths}
	{formatUsd}
	currencyCode={roiCurrencyCode}
	onTrackScenarioAdjust={trackScenarioAdjust}
	onScenarioWasteWithoutChange={handleScenarioWasteWithoutChange}
	onScenarioWasteWithChange={handleScenarioWasteWithChange}
	onScenarioWindowChange={handleScenarioWindowChange}
	{roiPlannerHref}
	{freeTierCtaHref}
	{buildPlanCtaHref}
	{plansTalkToSalesHref}
	{plansEnterpriseHref}
	{trustEnterpriseHref}
	{requestValidationBriefingHref}
	onePagerHref={ONE_PAGER_HREF}
	subscribeApiPath={SUBSCRIBE_API_PATH}
	resourcesHref={RESOURCES_PATH}
	onTrackCta={trackCta}
	{cookieBannerVisible}
	onSetTelemetryConsent={setTelemetryConsent}
	onCloseCookieBanner={closeCookieBanner}
	onOpenCookieSettings={openCookieSettings}
	{showBackToTop}
/>
