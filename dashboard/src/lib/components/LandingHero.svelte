<script lang="ts">
	import { browser } from '$app/environment';
	import { assets, base } from '$app/paths';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { LANDING_SIGNAL_SNAPSHOTS } from '$lib/landing/landingSignalSnapshots';
	import {
		resolveLandingExperiments,
		shouldIncludeExperimentQueryParams,
		type LandingExperimentAssignments
	} from '$lib/landing/landingExperiment';
	import {
		resolveDetectedLandingCurrency,
		resolveInitialLandingCurrency,
		setLandingCurrencyPreference,
		type LandingCurrencyCode
	} from '$lib/landing/currencyPreference';
	import type { LandingAttribution } from '$lib/landing/landingFunnel';
	import {
		DEFAULT_EXPERIMENT_ASSIGNMENTS,
		LANDING_CONSENT_KEY,
		LANDING_SCROLL_MILESTONES,
		resolveLandingMotionProfile,
		SNAPSHOT_ROTATION_MS
	} from '$lib/landing/landingHeroConfig';
	import {
		buildLandingHeroSalesPath,
		buildLandingHeroSignupPath
	} from '$lib/landing/landingHeroActions';
	import { createLandingHeroTelemetryBridge } from '$lib/landing/landingHeroTelemetryBridge';
	import { appendPublicAttribution } from '$lib/public/publicBuyingMotion';
	import {
		calculateLandingHeroScenarioMetrics,
		formatLandingHeroCurrencyAmount
	} from '$lib/landing/landingHeroScenario';
	import {
		DEFAULT_LANDING_ROI_INPUTS,
		normalizeLandingRoiInputs
	} from '$lib/landing/roiCalculator';
	import { getReducedMotionPreference } from '$lib/landing/reducedMotion';
	import { nextSnapshotIndex } from '$lib/landing/signalRotation';
	import { BUYER_ROLE_VIEWS, HERO_ROLE_CONTEXT } from '$lib/landing/heroContent';
	import LandingHeroView from '$lib/components/landing/LandingHeroView.svelte';
	const DEFAULT_SIGNAL_SNAPSHOT = LANDING_SIGNAL_SNAPSHOTS[0];
	const ONE_PAGER_HREF = `${base}/resources/valdrics-enterprise-one-pager.md`,
		RESOURCES_PATH = `${base}/resources`;
	const SUBSCRIBE_API_PATH = `${base}/api/marketing/subscribe`,
		TALK_TO_SALES_PATH = `${base}/talk-to-sales`,
		ENTERPRISE_PATH = `${base}/enterprise`;
	if (!DEFAULT_SIGNAL_SNAPSHOT)
		throw new Error('Landing signal snapshots require at least one snapshot.');
	let signalMapElement: HTMLDivElement | null = null;
	let signalMapInView = $state(true),
		documentVisible = $state(true),
		snapshotIndex = $state(0),
		buyerRoleIndex = $state(0);
	let visitorId = $state(''),
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
	let snapshotAutoplayPaused = $state(false);
	let prefersReducedMotion = $state(
		getReducedMotionPreference(browser && typeof window !== 'undefined' ? window : undefined)
	);
	let telemetryEnabled = $state(false),
		telemetryInitialized = $state(false),
		cookieBannerVisible = $state(false),
		localCurrencyCode = $state<LandingCurrencyCode>(resolveDetectedLandingCurrency()),
		roiCurrencyCode = $state<LandingCurrencyCode>(resolveInitialLandingCurrency());
	let activeSnapshot = $derived(LANDING_SIGNAL_SNAPSHOTS[snapshotIndex] ?? DEFAULT_SIGNAL_SNAPSHOT);
	let activeBuyerRole = $derived(BUYER_ROLE_VIEWS[buyerRoleIndex] ?? BUYER_ROLE_VIEWS[0]);
	let activeSignalLane = $derived(
		activeSnapshot.lanes.find(
			(lane) => lane.severity === 'watch' || lane.severity === 'critical'
		) ?? activeSnapshot.lanes[0]
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
	let secondaryCtaLabel = $derived(
		experiments.ctaVariant === 'book_briefing' ? 'Start Free Workspace' : 'See Pricing'
	);
	let secondaryCtaHref = $derived(
		experiments.ctaVariant === 'book_briefing'
			? buildSignupHref(heroContext.primaryIntent, { source: 'hero_secondary' })
			: buildPublicPath(`${base}/pricing`, 'hero_secondary')
	);
	let roiPlannerHref = $derived(buildSignupHref('roi_assessment', { source: 'simulator' }));
	let requestValidationBriefingHref = $derived(
			buildTalkToSalesHref('trust_validation', 'request_validation_briefing')
		),
		aboutHref = $derived(buildPublicPath(`${base}/about`, 'trust_about')),
		docsHref = $derived(buildPublicPath(`${base}/docs`, 'trust_docs')),
		statusHref = $derived(buildPublicPath(`${base}/status`, 'trust_status')),
		proofHref = $derived(buildPublicPath(`${base}/proof`, 'trust_proof')),
		plansEnterpriseHref = $derived(buildEnterpriseReviewHref('plans_enterprise')),
		trustEnterpriseHref = $derived(buildEnterpriseReviewHref('trust_enterprise'));
	let showBackToTop = $derived(landingScrollProgressPct >= 8),
		motionProfile = $derived(resolveLandingMotionProfile($page.url));
	let primaryCtaIntent = $derived(
		experiments.ctaVariant === 'book_briefing' ? 'executive_briefing' : heroContext.primaryIntent
	);
	let primaryCtaHref = $derived(
		experiments.ctaVariant === 'book_briefing'
			? buildTalkToSalesHref('hero_briefing', 'executive_briefing')
			: buildSignupHref(primaryCtaIntent)
	);
	let freeTierCtaHref = $derived(
		buildSignupHref('free_tier', { plan: 'free', source: 'free_tier' })
	);
	let secondaryCtaTelemetryValue = $derived(
		experiments.ctaVariant === 'book_briefing' ? 'start_free' : 'see_pricing'
	);
	let includeExperimentQueryParams = $derived(shouldIncludeExperimentQueryParams($page.url, false));
	let shouldRotateSnapshots = $derived(
		!snapshotAutoplayPaused &&
			!prefersReducedMotion &&
			documentVisible &&
			signalMapInView &&
			LANDING_SIGNAL_SNAPSHOTS.length > 1
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
		if (!shouldRotateSnapshots) return;
		const interval = setInterval(() => {
			snapshotIndex = nextSnapshotIndex(snapshotIndex, LANDING_SIGNAL_SNAPSHOTS.length);
		}, SNAPSHOT_ROTATION_MS);
		return () => clearInterval(interval);
	});
	onMount(() => {
		let cancelled = false;
		let teardown: (() => void) | void;

		void import('$lib/landing/landingHeroBrowserRuntime').then(
			({ mountLandingHeroBrowserRuntime }) => {
				if (cancelled) return;
				teardown = mountLandingHeroBrowserRuntime({
					browserEnabled: browser,
					windowRef: window,
					documentRef: document,
					signalMapElement,
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
				});
			}
		);

		return () => {
			cancelled = true;
			teardown?.();
		};
	});
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
	function buildTalkToSalesHref(source: string, intent?: string): string {
		return buildLandingHeroSalesPath({
			path: TALK_TO_SALES_PATH,
			source,
			intent,
			persona: activeBuyerRole.id,
			utm: attribution.utm
		});
	}
	function buildPublicPath(path: string, source: string): string {
		return appendPublicAttribution(path, $page.url, {
			entry: 'landing',
			source,
			persona: activeBuyerRole.id
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
	const handleScenarioWasteWithoutChange = (value: number) => (scenarioWasteWithoutPct = value);
	const handleScenarioWasteWithChange = (value: number) => (scenarioWasteWithPct = value);
	const handleScenarioWindowChange = (value: number) => (scenarioWindowMonths = value);
	const formatUsd = (amount: number, currency: string = roiCurrencyCode) =>
		formatLandingHeroCurrencyAmount(amount, currency);
	function handleCurrencyCodeChange(value: LandingCurrencyCode): void {
		roiCurrencyCode = value;
		setLandingCurrencyPreference(value);
	}
</script>

<LandingHeroView
	{motionProfile}
	{canonicalUrl}
	imageUrl={ogImageUrl}
	{heroTitle}
	{heroSubtitle}
	{primaryCtaLabel}
	{secondaryCtaLabel}
	{secondaryCtaHref}
	{primaryCtaHref}
	{secondaryCtaTelemetryValue}
	{activeSnapshot}
	{activeSignalLane}
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
	{localCurrencyCode}
	currencyCode={roiCurrencyCode}
	onCurrencyCodeChange={handleCurrencyCodeChange}
	onTrackScenarioAdjust={trackScenarioAdjust}
	onScenarioWasteWithoutChange={handleScenarioWasteWithoutChange}
	onScenarioWasteWithChange={handleScenarioWasteWithChange}
	onScenarioWindowChange={handleScenarioWindowChange}
	{roiPlannerHref}
	{freeTierCtaHref}
	{trustEnterpriseHref}
	{aboutHref}
	{docsHref}
	{statusHref}
	{proofHref}
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
