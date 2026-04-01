<script lang="ts">
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import type { LandingCurrencyCode } from '$lib/landing/currencyPreference';
	import { formatCurrencyAmount } from '$lib/landing/currencyDisplay';
	import { calculateLandingHeroScenarioMetrics } from '$lib/landing/landingHeroScenario';
	import { createLazyComponent } from '$lib/lazyComponent';
	import LandingHeroRoiPlaceholder from '$lib/components/landing/LandingHeroRoiPlaceholder.svelte';
	import type {
		LandingSignalLaneSnapshot,
		LandingSignalSnapshot
	} from '$lib/landing/landingSignalSnapshots';
	import type { SignalLaneId } from '$lib/landing/realtimeSignalMap';

	const publicLaneTitles: Record<SignalLaneId, string> = {
		economic_visibility: 'Signal captured',
		deterministic_enforcement: 'Checks applied',
		financial_governance: 'Approval routed',
		operational_resilience: 'Outcome recorded'
	};

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

	type LandingRoiSimulatorProps = {
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
		plannerHref: string;
		onTrackScenarioAdjust: (control: string) => void;
		onScenarioWasteWithoutChange: (value: number) => void;
		onScenarioWasteWithChange: (value: number) => void;
		onScenarioWindowChange: (value: number) => void;
		onTrackPlannerCta: () => void;
	};

	const loadLandingRoiSimulator = createLazyComponent<LandingRoiSimulatorProps>(
		() => import('$lib/components/landing/LandingRoiSimulator.svelte')
	);
	type LandingHeroTrustSectionsProps = {
		freeTierCtaHref: string;
		trustEnterpriseHref: string;
		aboutHref: string;
		docsHref: string;
		statusHref: string;
		proofHref?: string;
		requestValidationBriefingHref: string;
		onePagerHref: string;
		onTrackCta: (action: string, section: string, value: string) => void;
	};
	const loadLandingHeroTrustSections = createLazyComponent<LandingHeroTrustSectionsProps>(
		() => import('$lib/components/landing/LandingHeroTrustSections.svelte')
	);

	let {
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
		onTrackCta
	}: {
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
		onTrackCta: (action: string, section: string, value: string) => void;
	} = $props();

	let scenarioMetrics = $derived(
		calculateLandingHeroScenarioMetrics({
			monthlySpendUsd: roiMonthlySpendUsd,
			wasteWithoutPct: scenarioWasteWithoutPct,
			wasteWithPct: scenarioWasteWithPct,
			windowMonths: scenarioWindowMonths
		})
	);
	const formatUsd = (amount: number, currency: string = String(currencyCode)) =>
		formatCurrencyAmount(amount, currency);

	let simulatorAnchor: HTMLDivElement | null = $state(null);
	let simulatorVisible = $state(import.meta.env.MODE === 'test');
	let trustSectionsAnchor: HTMLDivElement | null = $state(null);
	let trustSectionsVisible = $state(import.meta.env.MODE === 'test');

	onMount(() => {
		if (simulatorVisible || typeof IntersectionObserver === 'undefined') {
			simulatorVisible = true;
			return;
		}

		const observer = new IntersectionObserver(
			(entries) => {
				if (entries.some((entry) => entry.isIntersecting)) {
					simulatorVisible = true;
					observer.disconnect();
				}
			},
			{ rootMargin: '420px 0px' }
		);

		if (simulatorAnchor) {
			observer.observe(simulatorAnchor);
		}

		return () => observer.disconnect();
	});

	onMount(() => {
		if (trustSectionsVisible || typeof IntersectionObserver === 'undefined') {
			trustSectionsVisible = true;
			return;
		}

		const observer = new IntersectionObserver(
			(entries) => {
				if (entries.some((entry) => entry.isIntersecting)) {
					trustSectionsVisible = true;
					observer.disconnect();
				}
			},
			{ rootMargin: '520px 0px' }
		);

		if (trustSectionsAnchor) {
			observer.observe(trustSectionsAnchor);
		}

		return () => observer.disconnect();
	});
</script>

<section id="product" class="landing-public-section" data-landing-section="product">
	<div class="container mx-auto px-6 py-12">
		<div class="landing-public-section-head">
			<p class="landing-public-eyebrow">Why it feels calmer</p>
			<h2>Replace reactive cleanup with one operating path</h2>
			<p>
				Most teams already know where the waste is. The hard part is ownership, approval, and proof.
				Valdrics keeps that work in one place.
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
					<strong>{publicLaneTitles[activeSignalLane.id] ?? activeSignalLane.id}</strong>
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

<div bind:this={simulatorAnchor}>
	{#if simulatorVisible}
		{#await loadLandingRoiSimulator() then module}
			{@const LandingRoiSimulator = module.default}
			<LandingRoiSimulator
				normalizedScenarioWasteWithoutPct={scenarioMetrics.normalizedScenarioWasteWithoutPct}
				normalizedScenarioWasteWithPct={scenarioMetrics.normalizedScenarioWasteWithPct}
				normalizedScenarioWindowMonths={scenarioMetrics.normalizedScenarioWindowMonths}
				scenarioWithoutBarPct={scenarioMetrics.scenarioWithoutBarPct}
				scenarioWithBarPct={scenarioMetrics.scenarioWithBarPct}
				scenarioWasteWithoutUsd={scenarioMetrics.scenarioWasteWithoutUsd}
				scenarioWasteWithUsd={scenarioMetrics.scenarioWasteWithUsd}
				scenarioWasteRecoveryMonthlyUsd={scenarioMetrics.scenarioWasteRecoveryMonthlyUsd}
				scenarioWasteRecoveryWindowUsd={scenarioMetrics.scenarioWasteRecoveryWindowUsd}
				monthlySpendUsd={roiMonthlySpendUsd}
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
		{:catch}
			<LandingHeroRoiPlaceholder />
		{/await}
	{:else}
		<LandingHeroRoiPlaceholder />
	{/if}
</div>

<div bind:this={trustSectionsAnchor}>
	{#if trustSectionsVisible}
		{#await loadLandingHeroTrustSections() then module}
			{@const LandingHeroTrustSections = module.default}
			<LandingHeroTrustSections
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
		{/await}
	{:else}
		<section
			id="plans"
			class="landing-public-section"
			data-landing-section="plans"
			aria-hidden="true"
		>
			<div class="container mx-auto px-6 py-12">
				<div class="landing-public-surface">
					<div class="skeleton mb-3 h-4 w-28"></div>
					<div class="skeleton mb-3 h-8 w-72"></div>
					<div class="skeleton h-4 w-full"></div>
				</div>
			</div>
		</section>
		<section
			id="trust"
			class="landing-public-section"
			data-landing-section="trust"
			aria-hidden="true"
		>
			<div class="container mx-auto px-6 py-12">
				<div class="landing-public-surface">
					<div class="skeleton mb-3 h-4 w-24"></div>
					<div class="skeleton mb-3 h-8 w-72"></div>
					<div class="skeleton h-4 w-full"></div>
				</div>
			</div>
		</section>
	{/if}
</div>
