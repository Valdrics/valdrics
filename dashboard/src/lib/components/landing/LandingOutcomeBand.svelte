<script lang="ts">
	type OutcomeMetric = {
		label: string;
		value: string;
	};

	type OutcomeState = {
		id: string;
		title: string;
		subtitle: string;
		ahaMoment: string;
		points: readonly string[];
		metrics: readonly OutcomeMetric[];
	};

	let {
		states
	}: {
		states: readonly OutcomeState[];
	} = $props();

	const reactiveState = $derived(states.find((state) => state.id === 'without') ?? states[0]);
	const governedState = $derived(
		states.find((state) => state.id === 'with') ?? states[1] ?? states[0]
	);
</script>

<section
	id="outcomes"
	class="container mx-auto px-6 pb-12 md:pb-14 landing-section-lazy"
	data-landing-section="outcomes"
>
	<div class="landing-section-head">
		<h2 class="landing-h2">The difference shows up after the alert</h2>
		<p class="landing-section-sub">
			Valdrics earns the next step: clear ownership, reviewable approvals, and evidence that
			survives the meeting.
		</p>
	</div>

	<div class="landing-outcome-grid">
		{#if reactiveState}
			<article class="glass-panel landing-outcome-card landing-outcome-card--reactive">
				<p class="landing-proof-k">Reactive path</p>
				<h3 class="landing-h3">{reactiveState.title}</h3>
				<p class="landing-outcome-summary">{reactiveState.subtitle}</p>
				<p class="landing-outcome-aha">{reactiveState.ahaMoment}</p>
				<ul class="landing-outcome-list">
					{#each reactiveState.points.slice(0, 3) as point (point)}
						<li>{point}</li>
					{/each}
				</ul>
				<div class="landing-outcome-metrics" aria-label="Reactive path indicators">
					{#each reactiveState.metrics.slice(0, 2) as metric (metric.label)}
						<div class="landing-outcome-metric">
							<p>{metric.label}</p>
							<strong>{metric.value}</strong>
						</div>
					{/each}
				</div>
			</article>
		{/if}

		{#if governedState}
			<article class="glass-panel landing-outcome-card landing-outcome-card--governed">
				<p class="landing-proof-k">Governed path</p>
				<h3 class="landing-h3">{governedState.title}</h3>
				<p class="landing-outcome-summary">{governedState.subtitle}</p>
				<p class="landing-outcome-aha">{governedState.ahaMoment}</p>
				<ul class="landing-outcome-list">
					{#each governedState.points.slice(0, 3) as point (point)}
						<li>{point}</li>
					{/each}
				</ul>
				<div class="landing-outcome-metrics" aria-label="Governed path indicators">
					{#each governedState.metrics.slice(0, 2) as metric (metric.label)}
						<div class="landing-outcome-metric">
							<p>{metric.label}</p>
							<strong>{metric.value}</strong>
						</div>
					{/each}
				</div>
			</article>
		{/if}
	</div>
</section>
