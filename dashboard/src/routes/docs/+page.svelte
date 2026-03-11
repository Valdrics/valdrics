<script lang="ts">
	import { base } from '$app/paths';
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';
	import PublicPageMeta from '$lib/components/public/PublicPageMeta.svelte';
	import { listPublicContent } from '$lib/content/publicContent';

	const docsEntries = listPublicContent('docs');

	const heroHighlights = [
		{
			label: 'Setup',
			value: 'Quick start, onboarding flow, and operating guidance'
		},
		{
			label: 'Validation',
			value: 'Technical validation and public proof links for buyer diligence'
		},
		{
			label: 'Reference',
			value: 'API docs, plan access, and legal commitments in one place'
		}
	] as const;
</script>

<PublicPageMeta
	title="Documentation"
	description="Valdrics documentation for setup, dashboard workflows, API usage, and operational guidance."
	pageType="CollectionPage"
	pageSection="Documentation"
	keywords={['documentation', 'api', 'technical validation', 'setup', 'governance']}
/>

<PublicMarketingPage
	kicker="Documentation"
	title="Documentation"
	subtitle="Use these guides to set up Valdrics quickly, align teams on spend ownership, and execute reliable cost decisions with confidence."
	heroVariant="narrow"
>
	{#snippet heroActions()}
		<a href={`${base}/docs/api`} class="btn btn-primary">Open API Docs</a>
		<a href={`${base}/docs/technical-validation`} class="btn btn-secondary">
			Open Technical Validation
		</a>
		<a href={`${base}/pricing`} class="btn btn-secondary">View Pricing</a>
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
		<section class="public-page__section" aria-labelledby="docs-sections-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Core guides</p>
				<h2 id="docs-sections-title" class="public-page__section-title">
					Pick the documentation surface that matches the question
				</h2>
				<p class="public-page__section-subtitle">
					Move from quick start to APIs, validation, resources, and policies without leaving the
					public documentation flow.
				</p>
			</div>

			<div class="public-page__grid public-page__grid--2">
				<article class="public-page__card public-page__card--dark">
					<h2 class="public-page__card-title">API Reference</h2>
					<p class="public-page__card-copy">
						Review endpoint groups and request examples for product and platform integrations.
					</p>
					<a href={`${base}/docs/api`} class="btn btn-secondary">Open API Docs</a>
				</article>

				<article class="public-page__card public-page__card--featured">
					<h2 class="public-page__card-title">Technical Validation</h2>
					<p class="public-page__card-copy">
						Review the buyer-safe capability-to-API validation summary used for technical diligence.
					</p>
					<a href={`${base}/docs/technical-validation`} class="btn btn-secondary">
						Open Technical Validation
					</a>
				</article>

				{#each docsEntries as entry (entry.slug)}
					<article
						class={`public-page__card ${
							entry.slug === 'quick-start-workspace'
								? 'public-page__card--accent public-page__card--featured'
								: ''
						}`}
					>
						<p class="public-page__card-kicker">{entry.kicker}</p>
						<h2 class="public-page__card-title">{entry.title}</h2>
						<p class="public-page__card-copy">{entry.summary}</p>
						<div class="public-page__actions-row">
							<a href={`${base}/docs/${entry.slug}`} class="btn btn-secondary">Open guide</a>
						</div>
					</article>
				{/each}
			</div>
		</section>

		<section class="public-page__section">
			<div class="public-page__band public-page__band--accent">
				<div class="public-page__band-copy">
					<p class="public-page__eyebrow">Repository docs</p>
					<h2 class="public-page__section-title">Repository Docs</h2>
					<p class="public-page__section-subtitle">
						Deployment and runbook documentation is maintained in the project repository.
					</p>
				</div>
				<div class="public-page__actions-row">
					<a
						href="https://github.com/Valdrics-AI/valdrics/tree/main/docs"
						target="_blank"
						rel="noopener noreferrer"
						class="btn btn-secondary"
					>
						Browse GitHub Docs
					</a>
				</div>
			</div>
		</section>
	{/snippet}
</PublicMarketingPage>
