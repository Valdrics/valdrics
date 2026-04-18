<script lang="ts">
	import { browser } from '$app/environment';
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import type { SignalLaneId } from '$lib/landing/realtimeSignalMap';
	import type { LandingCurrencyCode } from '$lib/landing/currencyPreference';
	import { formatCurrencyAmount } from '$lib/landing/currencyDisplay';
	import type {
		LandingSignalLaneSnapshot,
		LandingSignalSnapshot
	} from '$lib/landing/landingSignalSnapshots';
	import { createLazyComponent } from '$lib/lazyComponent';
	import LandingHeroCopy from '$lib/components/landing/LandingHeroCopy.svelte';
	import LandingHeroBelowFold from '$lib/components/landing/LandingHeroBelowFold.svelte';
	import './LandingMarketingShared.css';
	import '../LandingHero.footer.css';
	import './LandingHeroView.public.css';

	type LandingExitIntentPromptProps = {
		enabled?: boolean;
		selfServeHref: string;
		resourcesHref: string;
		subscribeApiPath: string;
		onTrackCta: (action: string, section: string, value: string) => void;
	};

	type LandingCookieConsentProps = {
		visible: boolean;
		onAccept: () => void;
		onReject: () => void;
		onClose: () => void;
	};

	const loadLandingExitIntentPrompt = createLazyComponent<LandingExitIntentPromptProps>(
		() => import('$lib/components/landing/LandingExitIntentPrompt.svelte')
	);
	const loadLandingCookieConsent = createLazyComponent<LandingCookieConsentProps>(
		() => import('$lib/components/landing/LandingCookieConsent.svelte')
	);

	const publicLaneTitles: Record<SignalLaneId, string> = {
		economic_visibility: 'Signal captured',
		deterministic_enforcement: 'Checks applied',
		financial_governance: 'Approval routed',
		operational_resilience: 'Outcome recorded'
	};

	function formatCapturedAt(value: string): string {
		const date = new Date(value);
		if (Number.isNaN(date.getTime())) return value;
		return new Intl.DateTimeFormat('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric'
		}).format(date);
	}

	const dashboardStillSrc = `${base}/landing-dashboard-still.jpg`;
	let exitPromptReady = $state(false);

	let {
		motionProfile,
		canonicalUrl,
		imageUrl,
		heroTitle,
		heroSubtitle,
		primaryCtaLabel,
		secondaryCtaLabel,
		secondaryCtaHref,
		primaryCtaHref,
		secondaryCtaTelemetryValue,
		activeSnapshot,
		activeSignalLane,
		roiMonthlySpendUsd,
		scenarioWasteWithoutPct,
		scenarioWasteWithPct,
		scenarioWindowMonths,
		currencyCode,
		localCurrencyCode,
		onCurrencyCodeChange = () => {},
		onTrackScenarioAdjust,
		onScenarioWasteWithoutChange,
		onScenarioWasteWithChange,
		onScenarioWindowChange,
		roiPlannerHref,
		freeTierCtaHref,
		trustEnterpriseHref,
		aboutHref,
		docsHref,
		statusHref,
		proofHref = '/proof',
		requestValidationBriefingHref,
		onePagerHref,
		subscribeApiPath,
		resourcesHref,
		onTrackCta,
		cookieBannerVisible,
		onSetTelemetryConsent,
		onCloseCookieBanner,
		onOpenCookieSettings,
		showBackToTop
	}: {
		motionProfile: 'subtle' | 'cinematic';
		canonicalUrl: string;
		imageUrl: string;
		heroTitle: string;
		heroSubtitle: string;
		primaryCtaLabel: string;
		secondaryCtaLabel: string;
		secondaryCtaHref: string;
		primaryCtaHref: string;
		secondaryCtaTelemetryValue: string;
		activeSnapshot: LandingSignalSnapshot;
		activeSignalLane: LandingSignalLaneSnapshot;
		roiMonthlySpendUsd: number;
		scenarioWasteWithoutPct: number;
		scenarioWasteWithPct: number;
		scenarioWindowMonths: number;
		currencyCode: LandingCurrencyCode | string;
		localCurrencyCode: LandingCurrencyCode;
		onCurrencyCodeChange?: (value: LandingCurrencyCode) => void;
		onTrackScenarioAdjust: (control: string) => void;
		onScenarioWasteWithoutChange: (value: number) => void;
		onScenarioWasteWithChange: (value: number) => void;
		onScenarioWindowChange: (value: number) => void;
		roiPlannerHref: string;
		freeTierCtaHref: string;
		trustEnterpriseHref: string;
		aboutHref: string;
		docsHref: string;
		statusHref: string;
		proofHref?: string;
		requestValidationBriefingHref: string;
		onePagerHref: string;
		subscribeApiPath: string;
		resourcesHref: string;
		onTrackCta: (action: string, section: string, value: string) => void;
		cookieBannerVisible: boolean;
		onSetTelemetryConsent: (accepted: boolean) => void;
		onCloseCookieBanner: () => void;
		onOpenCookieSettings: () => void;
		showBackToTop: boolean;
	} = $props();

	let highlightedWasteUsd = $derived(
		activeSignalLane.wasteUsd ??
			activeSnapshot.lanes.find((lane) => typeof lane.wasteUsd === 'number')?.wasteUsd ??
			12400
	);
	let highlightedActionLabel = $derived(activeSignalLane.actionLabel ?? 'Assign owner');
	let laneSeverityTone = $derived(activeSignalLane.severity ?? 'healthy');
	const formatPreviewAmount = (amount: number, currency: string = String(currencyCode)) =>
		formatCurrencyAmount(amount, currency);

	onMount(() => {
		if (import.meta.env.MODE === 'test') {
			exitPromptReady = true;
			return;
		}

		if (!browser) return;

		const activate = () => {
			exitPromptReady = true;
		};

		if (typeof window.requestIdleCallback === 'function') {
			const idleId = window.requestIdleCallback(activate, { timeout: 1500 });
			return () => window.cancelIdleCallback(idleId);
		}

		const timeoutId = window.setTimeout(activate, 800);
		return () => window.clearTimeout(timeoutId);
	});
</script>

<div
	class={`landing-public landing-motion-${motionProfile}`}
	itemscope
	itemtype="https://schema.org/SoftwareApplication"
>
	<meta itemprop="name" content="Valdrics" />
	<meta itemprop="operatingSystem" content="Web" />
	<meta itemprop="applicationCategory" content="BusinessApplication" />
	<meta
		itemprop="description"
		content="Valdrics helps finance and engineering teams move from spend signal to owner, approval, and proof in one governed path."
	/>
	<meta itemprop="url" content={canonicalUrl} />
	<meta itemprop="image" content={imageUrl} />

	<section id="hero" class="landing-public-hero" data-landing-section="hero">
		<div class="landing-public-hero-motion" aria-hidden="true">
			<span class="landing-public-hero-orb landing-public-hero-orb--left"></span>
			<span class="landing-public-hero-orb landing-public-hero-orb--right"></span>
			<span class="landing-public-hero-orb landing-public-hero-orb--pulse"></span>
			<span class="landing-public-hero-ring"></span>
		</div>
		<div class="container mx-auto px-6 py-10 sm:py-12 lg:py-16">
			<div class="landing-public-hero-grid">
				<LandingHeroCopy
					{heroTitle}
					{heroSubtitle}
					{primaryCtaLabel}
					{secondaryCtaLabel}
					{secondaryCtaHref}
					{primaryCtaHref}
					onPrimaryCta={() => onTrackCta('cta_click', 'hero', primaryCtaLabel.toLowerCase())}
					onSecondaryCta={() => onTrackCta('cta_click', 'hero', secondaryCtaTelemetryValue)}
				/>

				<aside
					class="landing-public-surface landing-public-product-still"
					aria-label="Real product dashboard screenshot"
				>
					<div class="landing-public-windowbar">
						<div class="landing-public-window-dots" aria-hidden="true">
							<span></span>
							<span></span>
							<span></span>
						</div>
						<p class="landing-public-window-title">
							Valdrics dashboard · {activeSnapshot.label}
						</p>
						<p class={`landing-public-window-status is-${laneSeverityTone}`}>
							{activeSignalLane.status}
						</p>
					</div>

					<figure class="landing-public-still-frame">
						<img
							class="landing-public-still-image"
							src={dashboardStillSrc}
							alt="Real Valdrics dashboard showing savings metrics, active findings, and owner-routed actions."
							width="1440"
							height="961"
							loading="eager"
							decoding="async"
							fetchpriority="high"
						/>
						<figcaption class="landing-public-still-caption">
							Real workspace still from the signed-in dashboard.
						</figcaption>
					</figure>

					<div class="landing-public-still-notes" aria-label="Why this screenshot matters">
						<article class="landing-public-still-note">
							<span>Decision record</span>
							<strong>{activeSnapshot.traceId}</strong>
							<small>{formatCapturedAt(activeSnapshot.capturedAt)}</small>
						</article>
						<article class="landing-public-still-note">
							<span>Current stage</span>
							<strong>{publicLaneTitles[activeSignalLane.id] ?? activeSignalLane.id}</strong>
							<small>{highlightedActionLabel}</small>
						</article>
						<article class="landing-public-still-note">
							<span>Linked proof</span>
							<strong>{activeSnapshot.sources.length} attached inputs</strong>
							<small
								>{formatPreviewAmount(highlightedWasteUsd, String(currencyCode))} at risk tracked</small
							>
						</article>
					</div>
				</aside>
			</div>

			<div class="landing-public-proof-strip" role="list" aria-label="Why teams choose Valdrics">
				<article class="landing-public-surface landing-public-proof-item" role="listitem">
					<p class="landing-public-proof-label">Rollout</p>
					<strong>First workflow typically live in 3-10 business days</strong>
				</article>
				<article class="landing-public-surface landing-public-proof-item" role="listitem">
					<p class="landing-public-proof-label">Operating model</p>
					<strong>Owner, approval, and proof stay on one operating record</strong>
				</article>
				<article class="landing-public-surface landing-public-proof-item" role="listitem">
					<p class="landing-public-proof-label">Open materials</p>
					<strong>Pricing, proof, docs, and company details are public</strong>
				</article>
			</div>
		</div>
	</section>

	<LandingHeroBelowFold
		{activeSnapshot}
		{activeSignalLane}
		{roiMonthlySpendUsd}
		{scenarioWasteWithoutPct}
		{scenarioWasteWithPct}
		{scenarioWindowMonths}
		{currencyCode}
		{localCurrencyCode}
		{onCurrencyCodeChange}
		{onTrackScenarioAdjust}
		{onScenarioWasteWithoutChange}
		{onScenarioWasteWithChange}
		{onScenarioWindowChange}
		{roiPlannerHref}
		{freeTierCtaHref}
		{trustEnterpriseHref}
		{aboutHref}
		{docsHref}
		{statusHref}
		{proofHref}
		{requestValidationBriefingHref}
		{onePagerHref}
		{onTrackCta}
	/>

	{#if showBackToTop}
		<a
			href="#hero"
			class="landing-back-to-top"
			onclick={() => onTrackCta('cta_click', 'utility', 'back_to_top')}
		>
			Back to top
		</a>
	{/if}

	{#if cookieBannerVisible}
		<div class="landing-cookie-banner-spacer" aria-hidden="true"></div>
		{#await loadLandingCookieConsent() then { default: LandingCookieConsent }}
			<LandingCookieConsent
				visible={cookieBannerVisible}
				onAccept={() => onSetTelemetryConsent(true)}
				onReject={() => onSetTelemetryConsent(false)}
				onClose={onCloseCookieBanner}
			/>
		{/await}
	{/if}

	{#if !cookieBannerVisible}
		<button type="button" class="landing-cookie-settings" onclick={onOpenCookieSettings}>
			Cookie Settings
		</button>
	{/if}

	{#if exitPromptReady}
		{#await loadLandingExitIntentPrompt() then { default: LandingExitIntentPrompt }}
			<LandingExitIntentPrompt
				enabled={!cookieBannerVisible}
				selfServeHref={freeTierCtaHref}
				{resourcesHref}
				{subscribeApiPath}
				{onTrackCta}
			/>
		{/await}
	{/if}
</div>

<style>
	.landing-cookie-banner-spacer {
		height: 13rem;
	}

	@media (max-width: 768px) {
		.landing-cookie-banner-spacer {
			height: 16rem;
		}
	}
</style>
