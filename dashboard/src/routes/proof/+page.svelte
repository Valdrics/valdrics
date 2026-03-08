<script lang="ts">
	import { base } from '$app/paths';
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';

	const heroHighlights = [
		{
			label: 'Control integrity',
			value: 'Signals, ownership, approvals, and proof tied together in one loop'
		},
		{
			label: 'Execution trace',
			value: 'Replayable approval chains, lane details, and recorded outcomes'
		},
		{
			label: 'Buyer-safe diligence',
			value: 'Public proof categories for leadership, finance, security, and platform review'
		}
	] as const;
</script>

<svelte:head>
	<title>Proof Pack | Valdrics</title>
	<meta
		name="description"
		content="Structured proof pack for Valdrics: control integrity, governance posture, deterministic execution, and operational resilience."
	/>
</svelte:head>

<PublicMarketingPage
	kicker="Proof Pack"
	title="Executive and technical proof for buyer diligence"
	subtitle="This page consolidates high-signal proof categories used during evaluation cycles across leadership, security, finance, and platform teams."
>
	{#snippet heroActions()}
		<a href={`${base}/docs`} class="btn btn-primary">Documentation</a>
		<a href={`${base}/docs/api`} class="btn btn-secondary">API Reference</a>
		<a href={`${base}/`} class="btn btn-secondary">Back to Landing</a>
	{/snippet}

	{#snippet heroMeta()}
		{#each heroHighlights as item (item.label)}
			<article class="public-page__meta-item">
				<strong>{item.label}</strong>
				<span>{item.value}</span>
			</article>
		{/each}
	{/snippet}

	{#snippet children()}
		<section class="public-page__section" aria-labelledby="proof-categories-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Proof categories</p>
				<h2 id="proof-categories-title" class="public-page__section-title">Review the evidence surface by buying concern</h2>
				<p class="public-page__section-subtitle">
					Each card below groups the public proof surface by the question buyers usually ask.
				</p>
			</div>

			<div class="public-page__grid public-page__grid--2">
				<article class="public-page__card public-page__card--dark">
					<h2 class="public-page__card-title">Economic Control Integrity</h2>
					<p class="public-page__card-copy">
						Signals, ownership, and policy checks are linked in one deterministic loop so financial
						decisions are made before month-end surprises.
					</p>
					<ul class="public-page__list">
						<li>Cross-surface visibility across cloud, SaaS, ITAM/license, and platform tooling.</li>
						<li>Buyer-mode narratives for CTO, FinOps, Security, and CFO priorities.</li>
						<li>Controlled section narratives for experimentation without message drift.</li>
					</ul>
				</article>

				<article class="public-page__card public-page__card--featured">
					<h2 class="public-page__card-title">Deterministic Execution</h2>
					<p class="public-page__card-copy">
						Execution pathways remain policy-led and replayable, with explicit approval contexts and
						snapshot-level traceability.
					</p>
					<ul class="public-page__list">
						<li>Realtime Signal Map snapshots with explicit lane severity classes.</li>
						<li>Lane-level detail drilldowns for operational interpretation.</li>
						<li>Deterministic variant assignment for controlled go-to-market experiments.</li>
					</ul>
				</article>

				<article class="public-page__card public-page__card--accent">
					<h2 class="public-page__card-title">Funnel and Attribution Telemetry</h2>
					<p class="public-page__card-copy">
						Landing analytics capture first-touch UTM context, stage-level progression, and CTA intent
						while keeping interaction dispatch non-blocking.
					</p>
					<ul class="public-page__list">
						<li>Tracked stages: view, engaged, CTA, and signup intent.</li>
						<li>Session funnel summary for conversion progression visibility.</li>
						<li>Telemetry payload context includes persona and experiment lineage.</li>
					</ul>
				</article>

				<article class="public-page__card">
					<h2 class="public-page__card-title">Operational Resilience and Accessibility</h2>
					<p class="public-page__card-copy">
						Landing UX hardening includes cleanup-safe intervals, tab semantics, reduced-motion
						behavior, and mobile-first tap target sizing.
					</p>
					<ul class="public-page__list">
						<li>No unbounded timers; lifecycle cleanup is tested.</li>
						<li>Interactive controls provide keyboard and ARIA pathways.</li>
						<li>Lazy section rendering improves perceived performance on long pages.</li>
					</ul>
				</article>
			</div>
		</section>

		<section class="public-page__section">
				<div class="public-page__band public-page__band--dark">
				<div class="public-page__band-copy">
					<p class="public-page__eyebrow">Next validation surfaces</p>
					<h2 class="public-page__section-title">Use the next layer of documentation only when you need it</h2>
					<p class="public-page__section-subtitle">
						Move from proof categories into product and API detail only when the buyer asks for deeper
						validation.
					</p>
				</div>
				<div class="public-page__actions-row">
					<a href={`${base}/docs`} class="btn btn-secondary">Documentation</a>
					<a href={`${base}/docs/api`} class="btn btn-secondary">API Reference</a>
					<a href={`${base}/pricing`} class="btn btn-secondary">Pricing</a>
					<a href={`${base}/`} class="btn btn-primary">Back to Landing</a>
				</div>
			</div>
		</section>
	{/snippet}
</PublicMarketingPage>
