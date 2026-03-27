<script lang="ts">
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

	let {
		currentStageLabel,
		actionLabel,
		sourceCount
	}: {
		currentStageLabel: string;
		actionLabel: string;
		sourceCount: number;
	} = $props();
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
					<strong>{currentStageLabel}</strong>
				</div>
				<div>
					<span>Action path</span>
					<strong>{actionLabel}</strong>
				</div>
				<div>
					<span>Linked sources</span>
					<strong>{sourceCount} attached inputs</strong>
				</div>
			</div>
		</div>
	</div>
</section>
