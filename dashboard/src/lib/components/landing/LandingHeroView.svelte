<script lang="ts">
	import { base } from '$app/paths';
	import type {
		SignalLaneId,
		SignalLaneSnapshot,
		SignalSnapshot
	} from '$lib/landing/realtimeSignalMap';
	import type { LandingCurrencyCode } from '$lib/landing/currencyPreference';
	import LandingHeroCopy from '$lib/components/landing/LandingHeroCopy.svelte';
	import LandingRoiSimulator from '$lib/components/landing/LandingRoiSimulator.svelte';
	import LandingCookieConsent from '$lib/components/landing/LandingCookieConsent.svelte';
	import LandingExitIntentPrompt from '$lib/components/landing/LandingExitIntentPrompt.svelte';
	import './LandingMarketingShared.css';
	import './LandingHeroView.public.css';

	const productPillars = [
		{
			title: 'See the issue with context',
			detail:
				'Cost, owner, approval, and policy context stay on one record instead of being rebuilt across dashboards and threads.'
		},
		{
			title: 'Route it to the right person',
			detail:
				'Engineering and finance move from the same operating record instead of chasing ownership in chat.'
		},
		{
			title: 'Finish with proof',
			detail:
				'Every material action keeps the decision trail and savings story ready for finance, security, or procurement review.'
		}
	] as const;

	const publicLaneTitles: Record<SignalLaneId, string> = {
		economic_visibility: 'Signal captured',
		deterministic_enforcement: 'Checks applied',
		financial_governance: 'Approval routed',
		operational_resilience: 'Outcome recorded'
	};

	const landingPlanPreview = [
		{
			name: 'Free',
			price: '$0',
			summary: 'Prove one owner-routed workflow without procurement overhead.',
			cta: 'Start Free Workspace',
			href: null
		},
		{
			name: 'Growth',
			price: '$149',
			summary:
				'Best fit for cross-functional teams that need shared cost ownership and collaboration.',
			cta: 'See Growth on Pricing',
			href: `${base}/pricing`
		},
		{
			name: 'Pro',
			price: '$299',
			summary:
				'Finance-grade controls, exports, and workflow depth without jumping straight into enterprise sales.',
			cta: 'Review Pro Details',
			href: `${base}/pricing`
		}
	] as const;

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
		activeSnapshot: SignalSnapshot;
		activeSignalLane: SignalLaneSnapshot;
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
							<strong>{publicLaneTitles[activeSignalLane.id] ?? activeSignalLane.title}</strong>
							<small>{highlightedActionLabel}</small>
						</article>
						<article class="landing-public-still-note">
							<span>Linked proof</span>
							<strong>{activeSnapshot.sources.length} attached inputs</strong>
							<small>{formatUsd(highlightedWasteUsd, currencyCode)} at risk tracked</small>
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

	<section id="product" class="landing-public-section" data-landing-section="product">
		<div class="container mx-auto px-6 py-12">
			<div class="landing-public-section-head">
				<p class="landing-public-eyebrow">Why it feels calmer</p>
				<h2>Replace reactive cleanup with one operating path</h2>
				<p>
					Most teams already know where the waste is. The hard part is ownership, approval, and
					proof. Valdrics keeps that work in one place.
				</p>
			</div>
			<div class="landing-public-pillar-grid">
				{#each productPillars as pillar (pillar.title)}
					<article class="landing-public-surface landing-public-pillar-card">
						<h3>{pillar.title}</h3>
						<p>{pillar.detail}</p>
					</article>
				{/each}
			</div>
			<div class="landing-public-band">
				<div>
					<p class="landing-public-eyebrow">What changes in practice</p>
					<h3>One record carries the issue from alert to decision</h3>
					<p>
						Finance, engineering, and leadership review the same story instead of rebuilding context
						from dashboards, tickets, and chat threads.
					</p>
				</div>
				<div class="landing-public-impact-grid">
					<div>
						<span>Current stage</span>
						<strong>{publicLaneTitles[activeSignalLane.id] ?? activeSignalLane.title}</strong>
					</div>
					<div>
						<span>Action path</span>
						<strong>{activeSignalLane.actionLabel ?? 'Assigned before review'}</strong>
					</div>
					<div>
						<span>Linked sources</span>
						<strong>{activeSnapshot.sources.length} attached inputs</strong>
					</div>
				</div>
			</div>
		</div>
	</section>

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
		{localCurrencyCode}
		{onCurrencyCodeChange}
		plannerHref={roiPlannerHref}
		{onTrackScenarioAdjust}
		{onScenarioWasteWithoutChange}
		{onScenarioWasteWithChange}
		{onScenarioWindowChange}
		onTrackPlannerCta={() => onTrackCta('cta_click', 'simulator', 'open_full_roi_planner')}
	/>

	<section id="plans" class="landing-public-section" data-landing-section="plans">
		<div class="container mx-auto px-6 py-12">
			<div class="landing-public-section-head">
				<p class="landing-public-eyebrow">Pricing</p>
				<h2>Pricing that matches rollout stage</h2>
				<p>
					Start small, prove the workflow, and only move up when the team needs more governance
					depth.
				</p>
			</div>
			<div class="landing-public-plan-grid">
				{#each landingPlanPreview as plan (plan.name)}
					<article class="landing-public-surface landing-public-plan-card">
						<p class="landing-public-proof-label">{plan.name}</p>
						<div class="landing-public-plan-price">{plan.price}</div>
						<p>{plan.summary}</p>
						{#if plan.href}
							<a
								href={plan.href}
								class="btn btn-secondary"
								onclick={() => onTrackCta('cta_click', 'plans', plan.name.toLowerCase())}
							>
								{plan.cta}
							</a>
						{:else}
							<a
								href={freeTierCtaHref}
								class="btn btn-primary"
								onclick={() => onTrackCta('cta_click', 'plans', 'free')}
							>
								{plan.cta}
							</a>
						{/if}
					</article>
				{/each}
			</div>
			<div class="landing-public-band landing-public-band--compact">
				<div>
					<p class="landing-public-eyebrow">Full pricing</p>
					<h3>Prices shown in USD.</h3>
					<p>
						Use the pricing page for full plan details. Contact enterprise for security,
						procurement, or deployment requirements.
					</p>
				</div>
				<div class="landing-public-band-actions">
					<a
						href={`${base}/pricing`}
						class="btn btn-secondary"
						onclick={() => onTrackCta('cta_click', 'plans', 'view_pricing')}
					>
						See Detailed Pricing
					</a>
					<a
						href={trustEnterpriseHref}
						class="btn btn-secondary"
						onclick={() => onTrackCta('cta_click', 'plans', 'enterprise_review')}
					>
						Enterprise Review
					</a>
				</div>
			</div>
		</div>
	</section>

	<section id="trust" class="landing-public-section" data-landing-section="trust">
		<div class="container mx-auto px-6 py-12">
			<div class="landing-public-section-head">
				<p class="landing-public-eyebrow">Trust</p>
				<h2>Review the company before you talk to us</h2>
				<p>Review the company, proof pack, and technical materials before you book a call.</p>
			</div>
			<div class="landing-public-trust-grid">
				<article class="landing-public-surface landing-public-trust-card">
					<p class="landing-public-proof-label">Proof pack</p>
					<h3>Start with the materials, not the pitch</h3>
					<p>Open the proof pack, one-pager, and technical validation notes directly.</p>
					<div class="landing-public-link-list">
						<a href={proofHref} onclick={() => onTrackCta('cta_click', 'trust', 'proof_pack')}>
							Open Proof Pack
						</a>
						<a href={onePagerHref} onclick={() => onTrackCta('cta_click', 'trust', 'one_pager')}>
							Download One-Pager
						</a>
						<a href={docsHref} onclick={() => onTrackCta('cta_click', 'trust', 'docs')}>
							Technical Validation
						</a>
					</div>
				</article>
				<article class="landing-public-surface landing-public-trust-card">
					<p class="landing-public-proof-label">Company</p>
					<h3>Know who is behind the product</h3>
					<p>
						Review the founder, company background, and public contact channels before procurement
						starts.
					</p>
					<div class="landing-public-link-list">
						<a href={aboutHref} onclick={() => onTrackCta('cta_click', 'trust', 'about')}
							>About / Team</a
						>
						<a href={statusHref} onclick={() => onTrackCta('cta_click', 'trust', 'status')}
							>Status Page</a
						>
					</div>
				</article>
				<article class="landing-public-surface landing-public-trust-card">
					<p class="landing-public-proof-label">Enterprise review</p>
					<h3>Use enterprise review when it is needed</h3>
					<p>
						Security, privacy, residency, and procurement questions can be handled separately
						without slowing down a basic evaluation.
					</p>
					<div class="landing-public-link-list">
						<a
							href={trustEnterpriseHref}
							onclick={() => onTrackCta('cta_click', 'trust', 'enterprise')}
						>
							Enterprise Review
						</a>
						<a
							href={requestValidationBriefingHref}
							onclick={() => onTrackCta('cta_click', 'trust', 'validation_briefing')}
						>
							Request Validation Briefing
						</a>
					</div>
				</article>
			</div>
		</div>
	</section>

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
