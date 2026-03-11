<script lang="ts">
	import type { LandingExperimentAssignments } from '$lib/landing/landingExperiment';
	import type {
		SignalLaneId,
		SignalLaneSnapshot,
		SignalSnapshot
	} from '$lib/landing/realtimeSignalMap';
	import CloudLogo from '$lib/components/CloudLogo.svelte';
	import LandingCloudHookSection from '$lib/components/landing/LandingCloudHookSection.svelte';
	import LandingHeroCopy from '$lib/components/landing/LandingHeroCopy.svelte';
	import LandingSignalMapCard from '$lib/components/landing/LandingSignalMapCard.svelte';
	import LandingRoiSimulator from '$lib/components/landing/LandingRoiSimulator.svelte';
	import LandingCapabilitiesSection from '$lib/components/landing/LandingCapabilitiesSection.svelte';
	import LandingPlansSection from '$lib/components/landing/LandingPlansSection.svelte';
	import LandingTrustSection from '$lib/components/landing/LandingTrustSection.svelte';
	import LandingCookieConsent from '$lib/components/landing/LandingCookieConsent.svelte';
	import LandingExitIntentPrompt from '$lib/components/landing/LandingExitIntentPrompt.svelte';

	let {
		motionProfile,
		landingScrollProgressPct,
		canonicalUrl,
		imageUrl,
		heroTitle,
		heroSubtitle,
		primaryCtaLabel,
		secondaryCtaLabel,
		secondaryCtaHref,
		primaryCtaHref,
		secondaryCtaTelemetryValue,
		ctaVariant,
		sectionOrderVariant,
		cloudHookStates,
		activeHookState,
		hookStateIndex,
		onSelectHookState,
		activeSnapshot,
		activeSignalLane,
		signalMapInView,
		snapshotIndex,
		demoStepIndex,
		onSelectSignalLane,
		onSelectDemoStep,
		onSelectSnapshot,
		onSignalMapElementChange,
		normalizedScenarioWasteWithoutPct,
		normalizedScenarioWasteWithPct,
		normalizedScenarioWindowMonths,
		scenarioWithoutBarPct,
		scenarioWithBarPct,
		scenarioWasteWithoutUsd,
		scenarioWasteWithUsd,
		scenarioWasteRecoveryMonthlyUsd,
		scenarioWasteRecoveryWindowUsd,
		monthlySpendUsd,
		scenarioWasteWithoutPct,
		scenarioWasteWithPct,
		scenarioWindowMonths,
		formatUsd,
		currencyCode,
		onTrackScenarioAdjust,
		onScenarioWasteWithoutChange,
		onScenarioWasteWithChange,
		onScenarioWindowChange,
		roiPlannerHref,
		freeTierCtaHref,
		buildPlanCtaHref,
		plansEnterpriseHref,
		trustEnterpriseHref,
		aboutHref,
		docsHref,
		statusHref,
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
		landingScrollProgressPct: number;
		canonicalUrl: string;
		imageUrl: string;
		heroTitle: string;
		heroSubtitle: string;
		primaryCtaLabel: string;
		secondaryCtaLabel: string;
		secondaryCtaHref: string;
		primaryCtaHref: string;
		secondaryCtaTelemetryValue: string;
		ctaVariant: LandingExperimentAssignments['ctaVariant'];
		sectionOrderVariant: LandingExperimentAssignments['sectionOrderVariant'];
		cloudHookStates: readonly {
			id: string;
			title: string;
			subtitle: string;
			ahaMoment: string;
			points: readonly string[];
			metrics: readonly { label: string; value: string }[];
		}[];
		activeHookState: {
			id: string;
			title: string;
			subtitle: string;
			ahaMoment: string;
			points: readonly string[];
			metrics: readonly { label: string; value: string }[];
		};
		hookStateIndex: number;
		onSelectHookState: (index: number) => void;
		activeSnapshot: SignalSnapshot;
		activeSignalLane: SignalLaneSnapshot;
		signalMapInView: boolean;
		snapshotIndex: number;
		demoStepIndex: number;
		onSelectSignalLane: (laneId: SignalLaneId) => void;
		onSelectDemoStep: (index: number) => void;
		onSelectSnapshot: (index: number) => void;
		onSignalMapElementChange: (element: HTMLDivElement | null) => void;
		normalizedScenarioWasteWithoutPct: number;
		normalizedScenarioWasteWithPct: number;
		normalizedScenarioWindowMonths: number;
		scenarioWithoutBarPct: number;
		scenarioWithBarPct: number;
		scenarioWasteWithoutUsd: number;
		scenarioWasteWithUsd: number;
		scenarioWasteRecoveryMonthlyUsd: number;
		scenarioWasteRecoveryWindowUsd: number;
		monthlySpendUsd: number;
		scenarioWasteWithoutPct: number;
		scenarioWasteWithPct: number;
		scenarioWindowMonths: number;
		formatUsd: (amount: number, currency?: string) => string;
		currencyCode: string;
		onTrackScenarioAdjust: (control: string) => void;
		onScenarioWasteWithoutChange: (value: number) => void;
		onScenarioWasteWithChange: (value: number) => void;
		onScenarioWindowChange: (value: number) => void;
		roiPlannerHref: string;
		freeTierCtaHref: string;
		buildPlanCtaHref: (planId: string) => string;
		plansEnterpriseHref: string;
		trustEnterpriseHref: string;
		aboutHref: string;
		docsHref: string;
		statusHref: string;
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
</script>

<div
	class={`landing landing-motion-${motionProfile}`}
	itemscope
	itemtype="https://schema.org/SoftwareApplication"
>
	<div class="landing-scroll-progress" aria-hidden="true">
		<span style={`width:${landingScrollProgressPct}%;`}></span>
	</div>
	<meta itemprop="name" content="Valdrics" />
	<meta itemprop="operatingSystem" content="Web" />
	<meta itemprop="applicationCategory" content="BusinessApplication" />
	<meta
		itemprop="description"
		content="Valdrics turns cloud, SaaS, and software spend signals into owner-routed approvals, remediation, workflow execution, and exportable proof."
	/>
	<meta itemprop="url" content={canonicalUrl} />
	<meta itemprop="image" content={imageUrl} />

	<section id="hero" class="landing-hero" data-landing-section="hero">
		<div class="landing-hero-signal-field" aria-hidden="true">
			<div class="landing-hero-signal-core">
				<CloudLogo provider="valdrics" size={136} />
			</div>
			<span class="landing-hero-signal-ring landing-hero-signal-ring-a"></span>
			<span class="landing-hero-signal-ring landing-hero-signal-ring-b"></span>
			<span class="landing-hero-signal-ring landing-hero-signal-ring-c"></span>
			<span class="landing-hero-signal-node landing-hero-signal-node-a"></span>
			<span class="landing-hero-signal-node landing-hero-signal-node-b"></span>
			<span class="landing-hero-signal-node landing-hero-signal-node-c"></span>
			<span class="landing-hero-signal-node landing-hero-signal-node-d"></span>
		</div>
		<div class="container mx-auto px-6 pt-7 pb-8 sm:pt-9 sm:pb-10 lg:pt-10 lg:pb-11">
			<LandingHeroCopy
				{heroTitle}
				{heroSubtitle}
				{primaryCtaLabel}
				{secondaryCtaLabel}
				{secondaryCtaHref}
				{primaryCtaHref}
				onPrimaryCta={() => onTrackCta('cta_click', 'hero', ctaVariant)}
				onSecondaryCta={() => onTrackCta('cta_click', 'hero', secondaryCtaTelemetryValue)}
			/>
		</div>
	</section>

	<LandingCloudHookSection
		{cloudHookStates}
		{activeHookState}
		{hookStateIndex}
		{onSelectHookState}
	/>

	<div class="landing-story-band">
		{#if sectionOrderVariant === 'workflow_first'}
			<section
				id="signal-map"
				class="container mx-auto px-6 pb-12 md:pb-16 landing-section-lazy"
				data-landing-section="signal_map"
			>
				<div class="landing-section-head">
					<h2 class="landing-h2">See the decision loop in action</h2>
					<p class="landing-section-sub">
						One live path from signal, to owner, to approval, to recorded outcome.
					</p>
				</div>
				<LandingSignalMapCard
					{activeSnapshot}
					{activeSignalLane}
					{signalMapInView}
					{snapshotIndex}
					{demoStepIndex}
					{onSelectSignalLane}
					{onSelectDemoStep}
					{onSelectSnapshot}
					{onSignalMapElementChange}
				/>
			</section>

			<div id="product">
				<LandingCapabilitiesSection />
			</div>
		{:else}
			<div id="product">
				<LandingCapabilitiesSection />
			</div>

			<section
				id="signal-map"
				class="container mx-auto px-6 pb-12 md:pb-16 landing-section-lazy"
				data-landing-section="signal_map"
			>
				<div class="landing-section-head">
					<h2 class="landing-h2">See the decision loop in action</h2>
					<p class="landing-section-sub">
						One live path from signal, to owner, to approval, to recorded outcome.
					</p>
				</div>
				<LandingSignalMapCard
					{activeSnapshot}
					{activeSignalLane}
					{signalMapInView}
					{snapshotIndex}
					{demoStepIndex}
					{onSelectSignalLane}
					{onSelectDemoStep}
					{onSelectSnapshot}
					{onSignalMapElementChange}
				/>
			</section>
		{/if}

		<LandingRoiSimulator
			{normalizedScenarioWasteWithoutPct}
			{normalizedScenarioWasteWithPct}
			{normalizedScenarioWindowMonths}
			{scenarioWithoutBarPct}
			{scenarioWithBarPct}
			{scenarioWasteWithoutUsd}
			{scenarioWasteWithUsd}
			{scenarioWasteRecoveryMonthlyUsd}
			{scenarioWasteRecoveryWindowUsd}
			{monthlySpendUsd}
			{scenarioWasteWithoutPct}
			{scenarioWasteWithPct}
			{scenarioWindowMonths}
			{formatUsd}
			{currencyCode}
			plannerHref={roiPlannerHref}
			{onTrackScenarioAdjust}
			{onScenarioWasteWithoutChange}
			{onScenarioWasteWithChange}
			{onScenarioWindowChange}
			onTrackPlannerCta={() => onTrackCta('cta_click', 'simulator', 'start_roi_assessment')}
		/>

		<LandingPlansSection
			buildFreeTierCtaHref={() => freeTierCtaHref}
			{buildPlanCtaHref}
			{onTrackCta}
		/>

		<LandingTrustSection
			onTrackCta={(value) => onTrackCta('cta_click', 'trust', value)}
			enterprisePathHref={trustEnterpriseHref}
			{aboutHref}
			{docsHref}
			{statusHref}
			{requestValidationBriefingHref}
			{onePagerHref}
		/>
	</div>

	<div class="landing-mobile-sticky-cta" aria-label="Mobile quick actions">
		<a
			href={primaryCtaHref}
			class="btn btn-primary"
			onclick={() => onTrackCta('cta_click', 'mobile_sticky', ctaVariant)}
		>
			{primaryCtaLabel}
		</a>
		<a
			href="#signal-map"
			class="btn btn-secondary"
			onclick={() => onTrackCta('cta_click', 'mobile_sticky', 'see_signal_map')}
		>
			See decision loop
		</a>
	</div>

	{#if showBackToTop}
		<a
			href="#hero"
			class="landing-back-to-top"
			onclick={() => onTrackCta('cta_click', 'utility', 'back_to_top')}
		>
			Back to top
		</a>
	{/if}

	<LandingCookieConsent
		visible={cookieBannerVisible}
		onAccept={() => onSetTelemetryConsent(true)}
		onReject={() => onSetTelemetryConsent(false)}
		onClose={onCloseCookieBanner}
	/>

	{#if !cookieBannerVisible}
		<button type="button" class="landing-cookie-settings" onclick={onOpenCookieSettings}>
			Cookie Settings
		</button>
	{/if}

	<LandingExitIntentPrompt
		selfServeHref={freeTierCtaHref}
		{resourcesHref}
		{subscribeApiPath}
		{onTrackCta}
	/>
</div>
