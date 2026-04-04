<script lang="ts">
	import { base } from '$app/paths';
	import type { LandingCurrencyCode } from '$lib/landing/currencyPreference';
	import { formatCurrencyAmount } from '$lib/landing/currencyDisplay';
	import { calculateLandingScenarioMetrics } from '$lib/landing/landingScenarioMetrics';
	import LandingCurrencyToggle from '$lib/components/landing/LandingCurrencyToggle.svelte';
	import './LandingMarketingShared.css';

	let {
		monthlySpendUsd,
		scenarioWasteWithoutPct,
		scenarioWasteWithPct,
		scenarioWindowMonths,
		onTrackScenarioAdjust,
		onScenarioWasteWithoutChange,
		onScenarioWasteWithChange,
		onScenarioWindowChange,
		onTrackPlannerCta,
		plannerHref,
		currencyCode,
		localCurrencyCode,
		onCurrencyCodeChange = () => {}
	}: {
		monthlySpendUsd: number;
		scenarioWasteWithoutPct: number;
		scenarioWasteWithPct: number;
		scenarioWindowMonths: number;
		onTrackScenarioAdjust: (control: string) => void;
		onScenarioWasteWithoutChange: (value: number) => void;
		onScenarioWasteWithChange: (value: number) => void;
		onScenarioWindowChange: (value: number) => void;
		onTrackPlannerCta: () => void;
		plannerHref: string;
		currencyCode: LandingCurrencyCode | string;
		localCurrencyCode: LandingCurrencyCode;
		onCurrencyCodeChange?: (value: LandingCurrencyCode) => void;
	} = $props();

	const scenarioMetrics = $derived(
		calculateLandingScenarioMetrics({
			monthlySpendUsd,
			wasteWithoutPct: scenarioWasteWithoutPct,
			wasteWithPct: scenarioWasteWithPct,
			windowMonths: scenarioWindowMonths
		})
	);
	const formatUsd = (amount: number, currency: string = String(currencyCode)) =>
		formatCurrencyAmount(amount, currency);

	function updateWasteWithout(event: Event): void {
		const value = Number((event.currentTarget as HTMLInputElement).value);
		onScenarioWasteWithoutChange(value);
		onTrackScenarioAdjust('reactive_waste_rate');
	}

	function updateWasteWith(event: Event): void {
		const value = Number((event.currentTarget as HTMLInputElement).value);
		onScenarioWasteWithChange(value);
		onTrackScenarioAdjust('governed_waste_rate');
	}

	function updateWindow(event: Event): void {
		const value = Number((event.currentTarget as HTMLInputElement).value);
		onScenarioWindowChange(value);
		onTrackScenarioAdjust('decision_window');
	}

	function updateCurrencyCode(value: LandingCurrencyCode): void {
		onCurrencyCodeChange(value);
	}
</script>

<section id="simulator" class="container mx-auto px-6 py-12" data-landing-section="simulator">
	<div class="landing-section-head">
		<div>
			<h2 class="landing-h2">Model the savings case in minutes</h2>
			<p class="landing-section-sub">
				Adjust a few operating assumptions and show the gap between reactive cleanup and governed
				execution.
			</p>
		</div>
		<LandingCurrencyToggle
			{currencyCode}
			{localCurrencyCode}
			onCurrencyCodeChange={updateCurrencyCode}
		/>
	</div>

	<div class="landing-sim-grid">
		<div class="landing-public-surface landing-sim-controls">
			<div class="landing-roi-control">
				<label for="sim-waste-without" class="landing-roi-label">Reactive waste rate (%)</label>
				<div class="landing-roi-meta">
					<span>{scenarioMetrics.normalizedScenarioWasteWithoutPct}%</span>
				</div>
				<input
					id="sim-waste-without"
					type="range"
					min="4"
					max="35"
					step="1"
					value={scenarioWasteWithoutPct}
					oninput={updateWasteWithout}
				/>
			</div>
			<div class="landing-roi-control">
				<label for="sim-waste-with" class="landing-roi-label">Managed waste rate (%)</label>
				<div class="landing-roi-meta">
					<span>{scenarioMetrics.normalizedScenarioWasteWithPct}%</span>
				</div>
				<input
					id="sim-waste-with"
					type="range"
					min="1"
					max={Math.max(1, scenarioMetrics.normalizedScenarioWasteWithoutPct - 1)}
					step="1"
					value={scenarioWasteWithPct}
					oninput={updateWasteWith}
				/>
			</div>
			<div class="landing-roi-control">
				<label for="sim-window" class="landing-roi-label">Decision window (months)</label>
				<div class="landing-roi-meta">
					<span>{scenarioMetrics.normalizedScenarioWindowMonths} months</span>
				</div>
				<input
					id="sim-window"
					type="range"
					min="3"
					max="24"
					step="1"
					value={scenarioWindowMonths}
					oninput={updateWindow}
				/>
			</div>
		</div>

		<div class="landing-public-surface landing-sim-results">
			<p class="landing-proof-k">Scenario Delta</p>
			<div class="landing-sim-metrics">
				<div class="landing-sim-metric is-highlight is-primary">
					<p>Potential monthly recovery</p>
					<strong>{formatUsd(scenarioMetrics.scenarioWasteRecoveryMonthlyUsd, currencyCode)}</strong
					>
					<span>Recoverable waste from reactive versus managed execution.</span>
				</div>
				<div class="landing-sim-metric is-highlight">
					<p>{scenarioMetrics.normalizedScenarioWindowMonths}-month recovery</p>
					<strong>{formatUsd(scenarioMetrics.scenarioWasteRecoveryWindowUsd, currencyCode)}</strong>
					<span>Directionally modeled over your selected decision window.</span>
				</div>
				<div class="landing-sim-metric is-context">
					<p>Spend context used</p>
					<strong>{formatUsd(monthlySpendUsd, currencyCode)} / month</strong>
				</div>
			</div>
			<div
				class="landing-sim-chart"
				role="img"
				aria-label="Reactive versus governed waste comparison"
			>
				<div class="landing-sim-bar-row">
					<div class="landing-sim-bar-label">Reactive spend</div>
					<progress
						class="landing-sim-bar-meter landing-sim-bar-meter--reactive"
						max="100"
						value={scenarioMetrics.scenarioWithoutBarPct}
					>
						{scenarioMetrics.scenarioWithoutBarPct}
					</progress>
					<div class="landing-sim-bar-value">
						{formatUsd(scenarioMetrics.scenarioWasteWithoutUsd, currencyCode)}
					</div>
				</div>
				<div class="landing-sim-bar-row">
					<div class="landing-sim-bar-label">Governed spend</div>
					<progress
						class="landing-sim-bar-meter landing-sim-bar-meter--governed"
						max="100"
						value={scenarioMetrics.scenarioWithBarPct}
					>
						{scenarioMetrics.scenarioWithBarPct}
					</progress>
					<div class="landing-sim-bar-value">
						{formatUsd(scenarioMetrics.scenarioWasteWithUsd, currencyCode)}
					</div>
				</div>
			</div>
			<p class="landing-roi-note">
				This model is directional. Use it to align finance and engineering around waste rate,
				decision timing, and rollout assumptions before building the full case.
				<a href={`${base}/docs/technical-validation`} class="landing-cta-link">Review methodology</a
				>
				<a href={`${base}/resources/valdrics-roi-assumptions.csv`} class="landing-cta-link">
					Open assumptions CSV
				</a>
			</p>
			<div class="landing-roi-cta">
				<p class="landing-proof-k">Need the full model?</p>
				<p class="landing-roi-note">
					Open the 12-month planner when you need rollout effort, implementation cost, and payback
					assumptions using your own numbers.
				</p>
				<a href={plannerHref} class="btn btn-primary w-fit" onclick={onTrackPlannerCta}>
					Open Full ROI Planner
				</a>
			</div>
		</div>
	</div>
</section>
