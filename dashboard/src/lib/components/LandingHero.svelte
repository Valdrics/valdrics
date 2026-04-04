<script lang="ts">
	import { browser } from '$app/environment';
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import type { LandingExperimentAssignments } from '$lib/landing/landingExperiment';
	import type { FunnelStage, LandingAttribution } from '$lib/landing/landingFunnel';
	import {
		LANDING_CONSENT_KEY,
		LANDING_SCROLL_MILESTONES,
		type LandingMotionProfile,
		SNAPSHOT_ROTATION_MS
	} from '$lib/landing/landingHeroConfig';
	import {
		buildLandingHeroSalesPath,
		buildLandingHeroSignupPath
	} from '$lib/landing/landingHeroActions';
	import {
		resolveInitialLandingCurrency,
		setLandingCurrencyPreference,
		type LandingCurrencyCode
	} from '$lib/landing/currencyPreference';
	import { buildLandingPublicPath } from '$lib/landing/landingPublicAttribution';
	import { LANDING_ROI_DEFAULTS } from '$lib/landing/landingRoiDefaults';
	import type { LandingTelemetryContext } from '$lib/landing/landingTelemetry';
	import { getReducedMotionPreference } from '$lib/landing/reducedMotion';
	import type {
		LandingSignalLaneSnapshot,
		LandingSignalSnapshot
	} from '$lib/landing/landingSignalSnapshots';
	import LandingHeroView from '$lib/components/landing/LandingHeroView.svelte';

	type LandingHeroTelemetryApi = {
		buildTelemetryContext: (stage?: FunnelStage) => LandingTelemetryContext;
		emitLandingTelemetrySafe: (
			name: string,
			section: string,
			value?: string,
			context?: LandingTelemetryContext
		) => void;
		markEngaged: () => void;
		initialize: () => void;
		setTelemetryConsent: (accepted: boolean) => void;
		trackCta: (action: string, section: string, value: string) => void;
		trackScenarioAdjust: (control: string) => void;
	};

	const ONE_PAGER_HREF = `${base}/resources/valdrics-enterprise-one-pager.md`;
	const RESOURCES_PATH = `${base}/resources`;
	const SUBSCRIBE_API_PATH = `${base}/api/marketing/subscribe`;
	const TALK_TO_SALES_PATH = `${base}/talk-to-sales`;
	const ENTERPRISE_PATH = `${base}/enterprise`;

	let {
		initialExperiments,
		includeExperimentQueryParams,
		initialMotionProfile,
		canonicalUrl,
		ogImageUrl,
		detectedCurrencyCode,
		buyerPersonaId,
		heroPrimaryIntent,
		heroTitle,
		heroSubtitle,
		initialSnapshot
	}: {
		initialExperiments: LandingExperimentAssignments;
		includeExperimentQueryParams: boolean;
		initialMotionProfile: LandingMotionProfile;
		canonicalUrl: string;
		ogImageUrl: string;
		detectedCurrencyCode: LandingCurrencyCode;
		buyerPersonaId: LandingExperimentAssignments['buyerPersonaDefault'];
		heroPrimaryIntent: string;
		heroTitle: string;
		heroSubtitle: string;
		initialSnapshot: LandingSignalSnapshot;
	} = $props();

	let signalMapElement: HTMLDivElement | null = null;
	let signalMapInView = $state(true);
	let documentVisible = $state(true);
	let snapshotIndex = $state(0);
	let hydratedSnapshotCatalog = $state<readonly LandingSignalSnapshot[]>([]);
	let snapshotAdvance = $state<((current: number, length: number) => number) | null>(null);
	let snapshotRuntimeLoaded = $state(false);
	let visitorId = $state('');
	let pageReferrer = $state('');
	let experimentOverrides = $state<LandingExperimentAssignments | null>(null);
	let attribution = $state<LandingAttribution>({ utm: {} });
	let engagedCaptured = $state(false);
	let roiMonthlySpendUsd = $state(LANDING_ROI_DEFAULTS.monthlySpendUsd);
	let scenarioWasteWithoutPct = $state(18);
	let scenarioWasteWithPct = $state(7);
	let scenarioWindowMonths = $state(12);
	let scenarioAdjustCaptured = $state(false);
	let landingScrollProgressPct = $state(0);
	let prefersReducedMotion = $state(
		getReducedMotionPreference(browser && typeof window !== 'undefined' ? window : undefined)
	);
	let telemetryEnabled = $state(false);
	let telemetryInitialized = $state(false);
	let cookieBannerVisible = $state(false);
	let roiCurrencyOverride = $state<LandingCurrencyCode | null>(null);
	let telemetryApi = $state<LandingHeroTelemetryApi | null>(null);
	let localCurrencyCode = $derived.by(() => detectedCurrencyCode);
	let roiCurrencyCode = $derived(
		roiCurrencyOverride ?? resolveInitialLandingCurrency(localCurrencyCode)
	);
	let experiments = $derived(experimentOverrides ?? initialExperiments);
	let snapshotCatalog = $derived(
		snapshotRuntimeLoaded ? hydratedSnapshotCatalog : [initialSnapshot]
	);
	let activeSnapshot = $derived(snapshotCatalog[snapshotIndex] ?? initialSnapshot);
	let activeSignalLane = $derived<LandingSignalLaneSnapshot>(
		activeSnapshot.lanes.find(
			(lane) => lane.severity === 'watch' || lane.severity === 'critical'
		) ??
			activeSnapshot.lanes[0] ??
			initialSnapshot.lanes[0]!
	);
	let primaryCtaLabel = $derived(
		experiments.ctaVariant === 'book_briefing' ? 'Book Executive Briefing' : 'Start Free Workspace'
	);
	let secondaryCtaLabel = $derived(
		experiments.ctaVariant === 'book_briefing' ? 'Start Free Workspace' : 'See Pricing'
	);
	let secondaryCtaHref = $derived(
		experiments.ctaVariant === 'book_briefing'
			? buildSignupHref(heroPrimaryIntent, { source: 'hero_secondary' })
			: buildPublicPath(`${base}/pricing`, 'hero_secondary')
	);
	let roiPlannerHref = $derived(buildSignupHref('roi_assessment', { source: 'simulator' }));
	let requestValidationBriefingHref = $derived(
		buildTalkToSalesHref('trust_validation', 'request_validation_briefing')
	);
	let aboutHref = $derived(buildPublicPath(`${base}/about`, 'trust_about'));
	let docsHref = $derived(buildPublicPath(`${base}/docs`, 'trust_docs'));
	let statusHref = $derived(buildPublicPath(`${base}/status`, 'trust_status'));
	let proofHref = $derived(buildPublicPath(`${base}/proof`, 'trust_proof'));
	let trustEnterpriseHref = $derived(buildEnterpriseReviewHref('trust_enterprise'));
	let showBackToTop = $derived(landingScrollProgressPct >= 8);
	let motionProfile = $derived(initialMotionProfile);
	let primaryCtaIntent = $derived(
		experiments.ctaVariant === 'book_briefing' ? 'executive_briefing' : heroPrimaryIntent
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
	let shouldRotateSnapshots = $derived(
		snapshotRuntimeLoaded &&
			!prefersReducedMotion &&
			documentVisible &&
			signalMapInView &&
			snapshotCatalog.length > 1
	);
	let telemetryBridgePromise: Promise<LandingHeroTelemetryApi> | null = null;
	let snapshotRuntimePromise: Promise<void> | null = null;

	const getCurrentPageUrl = (): URL =>
		browser && typeof window !== 'undefined'
			? new URL(window.location.href)
			: new URL(canonicalUrl);

	function buildFallbackTelemetryContext(stage?: FunnelStage): LandingTelemetryContext {
		const pageUrl = getCurrentPageUrl();
		return {
			visitorId,
			persona: buyerPersonaId,
			referrer: pageReferrer || undefined,
			pagePath: pageUrl.pathname,
			funnelStage: stage,
			experiment: {
				hero: experiments.heroVariant,
				cta: experiments.ctaVariant,
				order: experiments.sectionOrderVariant
			},
			utm: attribution.utm
		};
	}

	function buildTelemetryContext(stage?: FunnelStage): LandingTelemetryContext {
		return telemetryApi?.buildTelemetryContext(stage) ?? buildFallbackTelemetryContext(stage);
	}

	function emitLandingTelemetrySafe(
		name: string,
		section: string,
		value?: string,
		context?: LandingTelemetryContext
	): void {
		telemetryApi?.emitLandingTelemetrySafe(name, section, value, context);
	}

	function initializeTelemetry(): void {
		telemetryApi?.initialize();
	}

	function markEngaged(): void {
		if (telemetryApi) {
			telemetryApi.markEngaged();
			return;
		}

		void ensureTelemetryBridge().then((api) => api.markEngaged());
	}

	function trackCta(action: string, section: string, value: string): void {
		if (telemetryApi) {
			telemetryApi.trackCta(action, section, value);
			return;
		}

		void ensureTelemetryBridge().then((api) => api.trackCta(action, section, value));
	}

	function trackScenarioAdjust(control: string): void {
		if (telemetryApi) {
			telemetryApi.trackScenarioAdjust(control);
			return;
		}

		void ensureTelemetryBridge().then((api) => api.trackScenarioAdjust(control));
	}

	function setTelemetryConsent(accepted: boolean): void {
		telemetryEnabled = accepted;
		cookieBannerVisible = false;

		if (browser && typeof window !== 'undefined') {
			window.localStorage.setItem(LANDING_CONSENT_KEY, accepted ? 'accepted' : 'rejected');
		}

		void ensureTelemetryBridge().then((api) => api.setTelemetryConsent(accepted));
	}

	async function ensureTelemetryBridge(): Promise<LandingHeroTelemetryApi> {
		if (telemetryApi) {
			return telemetryApi;
		}

		if (!telemetryBridgePromise) {
			telemetryBridgePromise = import('$lib/landing/landingHeroTelemetryBridge')
				.then(({ createLandingHeroTelemetryBridge }) => {
					const nextTelemetryApi = createLandingHeroTelemetryBridge({
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
						setExperiments: (value) => (experimentOverrides = value),
						getAttribution: () => attribution,
						setAttribution: (value) => (attribution = value),
						getPersona: () => buyerPersonaId,
						getPagePath: () => getCurrentPageUrl().pathname,
						getReferrer: () => pageReferrer,
						getStorage: () => (browser ? window.localStorage : undefined),
						getPageUrl: () => getCurrentPageUrl(),
						consentStorageKey: LANDING_CONSENT_KEY
					});
					telemetryApi = nextTelemetryApi;
					return nextTelemetryApi;
				})
				.catch((error) => {
					telemetryBridgePromise = null;
					throw error;
				});
		}

		return telemetryBridgePromise;
	}

	async function ensureSnapshotRuntime(): Promise<void> {
		if (snapshotRuntimeLoaded) {
			return;
		}

		if (!snapshotRuntimePromise) {
			snapshotRuntimePromise = Promise.all([
				import('$lib/landing/landingSignalSnapshots'),
				import('$lib/landing/signalRotation')
			])
				.then(([{ LANDING_SIGNAL_SNAPSHOTS }, { nextSnapshotIndex }]) => {
					hydratedSnapshotCatalog = LANDING_SIGNAL_SNAPSHOTS;
					snapshotAdvance = nextSnapshotIndex;
					snapshotRuntimeLoaded = true;
				})
				.catch((error) => {
					snapshotRuntimePromise = null;
					throw error;
				});
		}

		return snapshotRuntimePromise;
	}

	$effect(() => {
		const advance = snapshotAdvance;
		if (!shouldRotateSnapshots || !advance) return;
		const interval = setInterval(() => {
			snapshotIndex = advance(snapshotIndex, snapshotCatalog.length);
		}, SNAPSHOT_ROTATION_MS);
		return () => clearInterval(interval);
	});

	onMount(() => {
		let cancelled = false;
		let teardown: (() => void) | void;

		const storedCurrency = resolveInitialLandingCurrency(localCurrencyCode);
		if (storedCurrency !== localCurrencyCode) {
			roiCurrencyOverride = storedCurrency;
		}

		void ensureSnapshotRuntime().catch(() => {
			// Decorative snapshot rotation must not block the landing experience.
		});

		void ensureTelemetryBridge()
			.then(() => import('$lib/landing/landingHeroBrowserRuntime'))
			.then(({ mountLandingHeroBrowserRuntime }) => {
				if (cancelled) return;
				teardown = mountLandingHeroBrowserRuntime({
					browserEnabled: browser,
					windowRef: window,
					documentRef: document,
					signalMapElement,
					consentStorageKey: LANDING_CONSENT_KEY,
					scrollMilestones: LANDING_SCROLL_MILESTONES,
					initializeTelemetry,
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
			})
			.catch(() => {
				// Telemetry/runtime failures must not block landing rendering.
			});

		return () => {
			cancelled = true;
			teardown?.();
		};
	});

	const closeCookieBanner = () => (cookieBannerVisible = false);
	const openCookieSettings = () => (cookieBannerVisible = true);

	function buildSignupHref(intent: string, extraParams: Record<string, string> = {}): string {
		return buildLandingHeroSignupPath({
			basePath: base,
			intent,
			persona: buyerPersonaId,
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
			persona: buyerPersonaId,
			utm: attribution.utm
		});
	}

	function buildPublicPath(path: string, source: string): string {
		return buildLandingPublicPath({
			path,
			source,
			persona: buyerPersonaId,
			utm: attribution.utm
		});
	}

	function buildEnterpriseReviewHref(source: string): string {
		return buildLandingHeroSalesPath({
			path: ENTERPRISE_PATH,
			source,
			persona: buyerPersonaId,
			utm: attribution.utm
		});
	}

	const handleScenarioWasteWithoutChange = (value: number) => (scenarioWasteWithoutPct = value);
	const handleScenarioWasteWithChange = (value: number) => (scenarioWasteWithPct = value);
	const handleScenarioWindowChange = (value: number) => (scenarioWindowMonths = value);
	function handleCurrencyCodeChange(value: LandingCurrencyCode): void {
		roiCurrencyOverride = value;
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
	{roiMonthlySpendUsd}
	{scenarioWasteWithoutPct}
	{scenarioWasteWithPct}
	{scenarioWindowMonths}
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
