<script lang="ts">
	import { BACKEND_CAPABILITY_PILLARS, DECISION_LEDGER_SUMMARY } from '$lib/landing/heroContent';
	import type {
		SignalLaneId,
		SignalLaneSnapshot,
		SignalSnapshot
	} from '$lib/landing/realtimeSignalMap';
	import LandingSignalMapCard from '$lib/components/landing/LandingSignalMapCard.svelte';

	let {
		activeSnapshot,
		activeSignalLane,
		signalMapInView,
		snapshotIndex,
		demoStepIndex,
		onSelectSignalLane,
		onSelectDemoStep,
		onSelectSnapshot,
		onSignalMapElementChange
	}: {
		activeSnapshot: SignalSnapshot;
		activeSignalLane: SignalLaneSnapshot;
		signalMapInView: boolean;
		snapshotIndex: number;
		demoStepIndex: number;
		onSelectSignalLane: (laneId: SignalLaneId) => void;
		onSelectDemoStep: (index: number) => void;
		onSelectSnapshot: (index: number) => void;
		onSignalMapElementChange: (element: HTMLDivElement | null) => void;
	} = $props();

	const productPillars = BACKEND_CAPABILITY_PILLARS.slice(0, 4);
	const summaryMetrics = DECISION_LEDGER_SUMMARY;
</script>

<section
	id="product"
	class="container mx-auto px-6 pb-16 landing-section-lazy"
	data-landing-section="product"
>
	<div class="landing-section-head">
		<h2 class="landing-h2">A governed operating layer after detection</h2>
		<p class="landing-section-sub">
			This is where Valdrics differentiates: the signal keeps its owner, checks, approvals,
			workflow, and proof all the way through execution.
		</p>
	</div>

	<div class="landing-product-grid">
		<div class="landing-product-primary">
			<div class="landing-product-summary glass-panel" aria-label="Operating loop summary">
				{#each summaryMetrics as item (item.label)}
					<div class="landing-product-summary-item">
						<p>{item.label}</p>
						<strong>{item.value}</strong>
					</div>
				{/each}
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
		</div>

		<div class="landing-product-support">
			{#each productPillars as pillar (pillar.title)}
				<article class="glass-panel landing-product-support-card">
					<p class="landing-proof-k">Capability</p>
					<h3 class="landing-h3">{pillar.title}</h3>
					<p class="landing-p">{pillar.detail}</p>
				</article>
			{/each}
		</div>
	</div>
</section>
