<script lang="ts">
	import { base } from '$app/paths';
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';
	import PublicPageMeta from '$lib/components/public/PublicPageMeta.svelte';
	import { listPublicContent } from '$lib/content/publicContent';

	const proofEntries = listPublicContent('proof');

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

<PublicPageMeta
	title="Proof Pack"
	description="Structured proof pack for Valdrics: control integrity, governance posture, deterministic execution, and operational resilience."
	pageType="WebPage"
	pageSection="Proof Pack"
	keywords={['proof pack', 'security', 'diligence', 'controls', 'technical validation']}
/>

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
				<h2 id="proof-categories-title" class="public-page__section-title">
					Review the evidence surface by buying concern
				</h2>
				<p class="public-page__section-subtitle">
					Each card below groups the public proof surface by the question buyers usually ask.
				</p>
			</div>

			<div class="public-page__grid public-page__grid--2">
				{#each proofEntries as entry (entry.slug)}
					<article
						class={`public-page__card ${
							entry.slug === 'identity-and-approval-controls'
								? 'public-page__card--dark'
								: entry.slug === 'validation-scope-and-operational-hardening'
									? 'public-page__card--accent public-page__card--featured'
									: 'public-page__card--featured'
						}`}
					>
						<p class="public-page__card-kicker">{entry.kicker}</p>
						<h2 class="public-page__card-title">{entry.title}</h2>
						<p class="public-page__card-copy">{entry.summary}</p>
						<ul class="public-page__list">
							{#each entry.sections[0]?.bullets ?? [] as bullet (bullet)}
								<li>{bullet}</li>
							{/each}
						</ul>
						<a href={`${base}/proof/${entry.slug}`} class="btn btn-secondary">Open proof page</a>
					</article>
				{/each}
			</div>
		</section>

		<section class="public-page__section">
			<div class="public-page__band public-page__band--dark">
				<div class="public-page__band-copy">
					<p class="public-page__eyebrow">Next validation surfaces</p>
					<h2 class="public-page__section-title">
						Use the next layer of documentation only when you need it
					</h2>
					<p class="public-page__section-subtitle">
						Move from proof categories into product and API detail only when the buyer asks for
						deeper validation.
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
